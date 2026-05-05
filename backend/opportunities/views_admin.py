import ast

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, Sum
from django.db.models import Max, OuterRef, Subquery
from django.conf import settings
from django.utils.timezone import now
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from config.celery import app as celery_app
from users.models import LoginEvent
from users.permissions import IsAdminUser
from .dataset_metrics import compute_pipeline_metrics
from .monitoring import collect_pipeline_anomalies
from .models import (
    Opportunite,
    PipelineRun,
    PipelineRunStatus,
    RawOpportunite,
    RawOpportuniteProcessingStatus,
)
from .source_cleanup import REMOVED_SOURCE_KEYS, removed_source_q
from .services.scheduler_monitoring import get_scheduler_decision_snapshots
from .utils.images import DEFAULT_COMPANY_LOGO_URL


User = get_user_model()


class AdminOpportunitySerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="titre", read_only=True)
    source = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source="date_creation", read_only=True)
    status = serializers.SerializerMethodField()
    url = serializers.URLField(source="source_item_url", read_only=True, allow_null=True)
    company_name = serializers.CharField(source="organisation_nom", read_only=True)

    class Meta:
        model = Opportunite
        fields = [
            "id",
            "title",
            "source",
            "created_at",
            "status",
            "url",
            "company_name",
        ]
        read_only_fields = fields

    def get_source(self, obj):
        if not obj.source_id:
            return None

        return {
            "id": obj.source_id,
            "nom": getattr(obj.source, "nom", None),
            "type_source": getattr(obj.source, "type_source", None),
        }

    def get_status(self, obj):
        value = getattr(obj, "statut", "")
        return str(value).lower()


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "is_admin", "is_active", "date_joined"]
        read_only_fields = fields


class AdminOpportunityViewSet(
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AdminOpportunitySerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = (
            Opportunite.objects.select_related("source")
            .exclude(removed_source_q("source__nom"))
            .order_by("-date_creation", "-id")
        )
        search = (self.request.query_params.get("search") or "").strip()
        source = (self.request.query_params.get("source") or "").strip()

        if search:
            queryset = queryset.filter(titre__icontains=search)

        if source:
            queryset = queryset.filter(source_id=source)

        return queryset


class AdminUserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all().order_by("-date_joined", "-id")

    @action(detail=True, methods=["post"], url_path="toggle-admin")
    def toggle_admin(self, request, pk=None):
        user = self.get_object()
        user.is_admin = not user.is_admin
        user.save(update_fields=["is_admin"])
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        user = self.get_object()

        if user.pk == request.user.pk and user.is_active:
            return Response(
                {"detail": "You cannot disable your own admin account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return Response(self.get_serializer(user).data)

PIPELINE_TASK_NAME = [
    "opportunities.collect_opportunities",
    "opportunities.collect_source",
    "opportunities.materialize_opportunities",
    "opportunities.generate_embeddings",
    "opportunities.monitor_pipeline",
]
PIPELINE_RUN_ONLY_FIELDS = (
    "started_at",
    "finished_at",
    "status",
    "processed_count",
    "created_count",
    "updated_count",
    "total_processed",
    "total_created",
    "total_updated",
    "total_failed_pages",
    "source",
    "duration_seconds",
    "error_message",
    "is_stale",
)


class AdminTestView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({"detail": "admin access ok"})


class AdminLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = self._find_user_by_credentials(email, password)
        if not user:
            return Response(
                {"detail": "Invalid admin credentials."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_admin:
            return Response(
                {"detail": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        LoginEvent.record(user, request)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "is_admin": user.is_admin,
                },
            },
            status=status.HTTP_200_OK,
        )

    def _find_user_by_credentials(self, email, password):
        users = User.objects.filter(email__iexact=email, is_active=True).order_by(
            "-is_admin",
            "id",
        )
        for user in users:
            if user.check_password(password):
                return user
        return None


def _get_celery_snapshot():
    try:
        inspector = celery_app.control.inspect(
            timeout=min(settings.ADMIN_DASHBOARD_CELERY_INSPECT_TIMEOUT, 2.0)
        )
        active = inspector.active() or {}
        scheduled = inspector.scheduled() or {}
        reserved = inspector.reserved() or {}
    except Exception:
        return {
            "workers": 0,
            "active_tasks": 0,
            "scheduled_tasks": 0,
            "reserved_tasks": 0,
            "queue_length": 0,
            "status": "degraded",
            "pipeline_running": False,
            "running_sources": [],
        }

    active_tasks = sum(len(tasks) for tasks in active.values())
    scheduled_tasks = sum(len(tasks) for tasks in scheduled.values())
    reserved_tasks = sum(len(tasks) for tasks in reserved.values())
    queue_length = active_tasks + reserved_tasks + scheduled_tasks
    pipeline_running = any(
        _is_pipeline_task(task)
        for tasks in active.values()
        for task in tasks
    )
    running_sources = sorted(
        {
            source
            for tasks in active.values()
            for task in tasks
            if _is_collect_source_task(task)
            for source in [_task_first_arg(task)]
            if source
        }
    )
    workers = len(set(active.keys()) | set(scheduled.keys()) | set(reserved.keys()))

    return {
        "workers": workers,
        "active_tasks": active_tasks,
        "scheduled_tasks": scheduled_tasks,
        "reserved_tasks": reserved_tasks,
        "queue_length": queue_length,
        "status": "healthy" if workers > 0 else "degraded",
        "pipeline_running": pipeline_running,
        "running_sources": running_sources,
    }


def _is_pipeline_task(task):
    task_name = task.get("name") or ""
    return any(name in task_name for name in PIPELINE_TASK_NAME)


def _is_collect_source_task(task):
    task_name = task.get("name") or ""
    return "collect_source" in task_name


def _task_first_arg(task):
    args = task.get("args")
    if isinstance(args, (list, tuple)):
        return args[0] if args else None
    if isinstance(args, str):
        try:
            parsed_args = ast.literal_eval(args)
        except (SyntaxError, ValueError):
            return None
        if isinstance(parsed_args, (list, tuple)):
            return parsed_args[0] if parsed_args else None
    return None


def _run_total(run, total_field, legacy_field):
    value = getattr(run, total_field, 0) or 0
    if value:
        return value
    return getattr(run, legacy_field, 0) or 0


def get_pipeline_stats():
    aggregates = PipelineRun.objects.exclude(source__in=REMOVED_SOURCE_KEYS).aggregate(
        total_runs=Count("id"),
        success_runs=Count("id", filter=Q(status=PipelineRunStatus.SUCCESS)),
        failed_runs=Count("id", filter=Q(status=PipelineRunStatus.FAILED)),
        total_processed=Sum("total_processed"),
        total_created=Sum("total_created"),
        total_updated=Sum("total_updated"),
        total_failed_pages=Sum("total_failed_pages"),
        avg_duration=Avg("duration_seconds"),
    )
    total_processed = aggregates.get("total_processed") or 0
    total_created = aggregates.get("total_created") or 0
    total_updated = aggregates.get("total_updated") or 0
    total_failed_pages = aggregates.get("total_failed_pages") or 0
    success_rate = ((total_created + total_updated) / total_processed) * 100 if total_processed else 0.0

    return {
        "total_runs": aggregates.get("total_runs") or 0,
        "success_runs": aggregates.get("success_runs") or 0,
        "failed_runs": aggregates.get("failed_runs") or 0,
        "total_processed": total_processed,
        "total_created": total_created,
        "total_updated": total_updated,
        "total_failed_pages": total_failed_pages,
        "success_rate": success_rate,
        "avg_duration": aggregates.get("avg_duration") or 0.0,
    }


def get_source_monitoring(running_sources=None):
    running_sources = set(running_sources or [])
    last_failed_run = (
        PipelineRun.objects.filter(
            source=OuterRef("source"),
            status=PipelineRunStatus.FAILED,
        )
        .order_by("-started_at", "-id")
        .values("error_message")[:1]
    )
    source_rows = (
        PipelineRun.objects.exclude(source__in=REMOVED_SOURCE_KEYS)
        .values("source")
        .annotate(
            total_runs=Count("id"),
            success_runs=Count("id", filter=Q(status=PipelineRunStatus.SUCCESS)),
            failed_runs=Count("id", filter=Q(status=PipelineRunStatus.FAILED)),
            total_processed=Sum("total_processed"),
            total_created=Sum("total_created"),
            total_updated=Sum("total_updated"),
            total_failed_pages=Sum("total_failed_pages"),
            avg_duration=Avg("duration_seconds"),
            last_run=Max("started_at"),
            last_error_message=Subquery(last_failed_run),
        )
        .order_by("source")
    )

    sources = []
    for row in source_rows:
        source = row.get("source")
        total_processed = row.get("total_processed") or 0
        total_created = row.get("total_created") or 0
        total_updated = row.get("total_updated") or 0
        success_rate = (
            ((total_created + total_updated) / total_processed) * 100
            if total_processed
            else 0.0
        )

        sources.append(
            {
                "source": source,
                "total_runs": row.get("total_runs") or 0,
                "success_runs": row.get("success_runs") or 0,
                "failed_runs": row.get("failed_runs") or 0,
                "total_processed": total_processed,
                "total_created": total_created,
                "total_updated": total_updated,
                "total_failed_pages": row.get("total_failed_pages") or 0,
                "avg_duration": row.get("avg_duration") or 0.0,
                "last_run": row.get("last_run"),
                "last_error_message": row.get("last_error_message"),
                "success_rate": success_rate,
                "is_running": source in running_sources,
            }
        )

    return sources


def get_embedding_monitoring():
    queryset = Opportunite.objects.exclude(removed_source_q("source__nom"))
    total = queryset.count()
    with_embeddings = queryset.exclude(embedding_vector__isnull=True).count()
    with_pg_embeddings = queryset.exclude(embedding_vector_pg__isnull=True).count()
    missing_embeddings = max(total - with_embeddings, 0)
    coverage = (with_embeddings / total) * 100 if total else 0.0

    return {
        "total": total,
        "with_embeddings": with_embeddings,
        "with_pg_embeddings": with_pg_embeddings,
        "missing_embeddings": missing_embeddings,
        "coverage": coverage,
        "is_complete": missing_embeddings == 0,
    }


def get_logo_monitoring():
    queryset = Opportunite.objects.exclude(removed_source_q("source__nom"))
    total = queryset.count()
    with_logo = queryset.exclude(company_logo="").exclude(company_logo=DEFAULT_COMPANY_LOGO_URL).count()
    missing_or_placeholder = max(total - with_logo, 0)
    coverage = (with_logo / total) * 100 if total else 0.0

    return {
        "total": total,
        "with_logo": with_logo,
        "missing_or_placeholder": missing_or_placeholder,
        "coverage": coverage,
    }


def get_pipeline_lag_monitoring():
    raw_statuses = (
        RawOpportunite.objects.exclude(removed_source_q("source__nom"))
        .values("processing_status")
        .annotate(count=Count("id"))
    )
    status_counts = {row["processing_status"]: row["count"] for row in raw_statuses}
    new_raw = int(status_counts.get(RawOpportuniteProcessingStatus.NEW, 0) or 0)

    return {
        "new_raw_remaining": new_raw,
        "raw_total": sum(int(count or 0) for count in status_counts.values()),
        "raw_status_counts": status_counts,
        "backlog_detected": new_raw > 0,
    }


def _serialize_pipeline_run(run):
    processed = _run_total(run, "total_processed", "processed_count")
    created = _run_total(run, "total_created", "created_count")
    updated = _run_total(run, "total_updated", "updated_count")
    success_rate = ((created + updated) / processed * 100) if processed else 0.0

    return {
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "status": run.status,
        "processed": processed,
        "created": created,
        "updated": updated,
        "failed_pages": run.total_failed_pages,
        "source": run.source,
        "duration_seconds": run.duration_seconds,
        "error_message": run.error_message,
        "is_stale": run.is_stale,
        "success_rate": success_rate,
    }


class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = now().date()
        total_opportunities = Opportunite.objects.exclude(removed_source_q("source__nom")).count()
        opportunities_today = RawOpportunite.objects.exclude(
            removed_source_q("source__nom")
        ).filter(last_seen_at__date=today).count()
        sources_count = (
            Opportunite.objects.exclude(removed_source_q("source__nom"))
            .values("source")
            .distinct()
            .count()
        )
        latest_run = (
            PipelineRun.objects.exclude(source__in=REMOVED_SOURCE_KEYS)
            .only(*PIPELINE_RUN_ONLY_FIELDS)
            .order_by("-started_at")
            .first()
        )
        recent_runs = list(
            PipelineRun.objects.exclude(source__in=REMOVED_SOURCE_KEYS)
            .only(*PIPELINE_RUN_ONLY_FIELDS)
            .order_by("-started_at")[:5]
        )
        last_failure = (
            PipelineRun.objects.exclude(source__in=REMOVED_SOURCE_KEYS)
            .only(*PIPELINE_RUN_ONLY_FIELDS)
            .filter(status=PipelineRunStatus.FAILED)
            .order_by("-started_at")
            .first()
        )
        sources = list(
            Opportunite.objects.exclude(removed_source_q("source__nom"))
            .values("source__nom")
            .annotate(count=Count("id"))
            .order_by("-count", "source__nom")
        )
        celery = _get_celery_snapshot()
        pipeline_stats = get_pipeline_stats()
        pipeline_metrics = compute_pipeline_metrics()
        monitoring_sources = get_source_monitoring(celery.get("running_sources", []))
        embedding_monitoring = get_embedding_monitoring()
        logo_monitoring = get_logo_monitoring()
        pipeline_lag = get_pipeline_lag_monitoring()
        alerts = collect_pipeline_anomalies()
        latest_processed = _run_total(latest_run, "total_processed", "processed_count") if latest_run else 0
        latest_created = _run_total(latest_run, "total_created", "created_count") if latest_run else 0
        latest_updated = _run_total(latest_run, "total_updated", "updated_count") if latest_run else 0
        pipeline_running = celery.get("pipeline_running", False)
        celery_response = {
            key: value
            for key, value in celery.items()
            if key not in {"pipeline_running", "running_sources"}
        }

        return Response(
            {
                "kpis": {
                    "total_opportunities": total_opportunities,
                    "pipeline_activity_today": opportunities_today,
                    "sources_count": sources_count,
                    "success_rate": pipeline_stats["success_rate"],
                    "logo_coverage": logo_monitoring["coverage"],
                },
                "pipeline": {
                    "last_run": latest_run.finished_at if latest_run else None,
                    "status": "running" if pipeline_running else "idle",
                    "processed": latest_processed,
                    "created": latest_created,
                    "updated": latest_updated,
                    "last_run_processed": pipeline_metrics["last_run_processed"],
                    "last_run_created": pipeline_metrics["last_run_created"],
                    "last_run_updated": pipeline_metrics["last_run_updated"],
                    "last_run_duration": pipeline_metrics["last_run_duration"],
                    "last_run_status": pipeline_metrics["last_run_status"],
                    "flow": pipeline_metrics["pipeline_flow"],
                    "failed_pages": latest_run.total_failed_pages if latest_run else 0,
                    "is_stale": latest_run.is_stale if latest_run else False,
                    "stats": pipeline_stats,
                    "duration_seconds": latest_run.duration_seconds if latest_run else 0.0,
                    "history": [_serialize_pipeline_run(run) for run in recent_runs],
                    "last_failure": _serialize_pipeline_run(last_failure) if last_failure else None,
                },
                "sources": [
                    {
                        "name": item["source__nom"] or "Unknown",
                        "count": item["count"],
                    }
                    for item in sources
                ],
                "celery": celery_response,
                "monitoring": {
                    "sources": monitoring_sources,
                    "queue": celery_response,
                    "embeddings": embedding_monitoring,
                    "logos": logo_monitoring,
                    "pipeline_lag": pipeline_lag,
                    "data_quality": pipeline_metrics["data_quality"],
                    "source_reliability_score": pipeline_metrics["source_reliability_score"],
                    "pipeline_throughput": pipeline_metrics["pipeline_throughput"],
                    "freshness_delay": pipeline_metrics["freshness_delay"],
                    "alerts": alerts,
                },
            }
        )


class AdminSchedulerStateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(get_scheduler_decision_snapshots())
