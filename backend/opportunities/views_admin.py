import ast
import csv
from collections import Counter
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.db.models import DateTimeField, Max, OuterRef, Subquery
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import now
from django_filters import rest_framework as django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from config.celery import app as celery_app
from users.models import AuditLog, LoginEvent, ProfileResume, Profil
from users.permissions import IsAdminUser
from users.serializers import UserSuspensionSerializer
from applications.models import Candidature
from .dataset_metrics import compute_pipeline_metrics
from .monitoring import collect_pipeline_anomalies
from .models import (
    Opportunite,
    PipelineRun,
    PipelineRunStatus,
    RawOpportunite,
    RawOpportuniteProcessingStatus,
    StatutOpportunite,
)
from .pipeline import get_source_schedule_state
from .source_cleanup import REMOVED_SOURCE_KEYS, removed_source_q
from .tasks import send_organization_admin_decision_email_task
from .services.scheduler_monitoring import get_scheduler_decision_snapshots
from .utils.images import DEFAULT_COMPANY_LOGO_URL


User = get_user_model()


class AdminOpportunitySerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="titre", read_only=True)
    description = serializers.CharField(read_only=True)
    type = serializers.CharField(source="type_opportunite", read_only=True)
    source = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source="date_creation", read_only=True)
    published_at = serializers.DateField(source="date_publication", read_only=True)
    status = serializers.SerializerMethodField()
    url = serializers.URLField(source="source_item_url", read_only=True, allow_null=True)
    company_name = serializers.CharField(source="organisation_nom", read_only=True)
    organization_email = serializers.EmailField(source="organisation.email", read_only=True, allow_null=True)
    location = serializers.CharField(source="ville", read_only=True)
    contract = serializers.CharField(source="contract_type", read_only=True)
    availability = serializers.CharField(read_only=True)
    salary = serializers.CharField(read_only=True)
    experience_min = serializers.IntegerField(read_only=True, allow_null=True)
    experience_max = serializers.IntegerField(read_only=True, allow_null=True)
    skills = serializers.ListField(child=serializers.CharField(), read_only=True)
    opportunity_details = serializers.SerializerMethodField()
    published_by = serializers.SerializerMethodField()
    moderation_summary = serializers.SerializerMethodField()

    class Meta:
        model = Opportunite
        fields = [
            "id",
            "title",
            "description",
            "type",
            "source",
            "created_at",
            "published_at",
            "status",
            "url",
            "company_name",
            "organization_email",
            "location",
            "contract",
            "availability",
            "salary",
            "experience_min",
            "experience_max",
            "skills",
            "opportunity_details",
            "published_by",
            "moderation_summary",
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
        return getattr(obj, "statut", "") or ""

    def get_published_by(self, obj):
        extra_data = getattr(obj, "extra_data", None)
        if isinstance(extra_data, dict):
            return extra_data.get("published_by") or "scraper"
        return "scraper"

    def get_opportunity_details(self, obj):
        extra_data = getattr(obj, "extra_data", None)
        if not isinstance(extra_data, dict):
            return {}
        details = {}
        for key in ("project_details", "internship_details", "seasonal_details"):
            if isinstance(extra_data.get(key), dict):
                details[key] = extra_data[key]
        return details

    def get_moderation_summary(self, obj):
        extra_data = getattr(obj, "extra_data", None)
        if not isinstance(extra_data, dict):
            return None
        moderation = extra_data.get("moderation")
        if not isinstance(moderation, dict):
            return None

        llm = moderation.get("llm") if isinstance(moderation.get("llm"), dict) else {}
        return {
            "final_decision": moderation.get("final_decision"),
            "final_status": moderation.get("final_status"),
            "category": llm.get("category"),
            "decision": llm.get("decision"),
            "confidence": llm.get("confidence"),
            "reason": llm.get("reason"),
            "provider": llm.get("provider"),
            "model": llm.get("model"),
        }


class AdminPendingOrganizationOpportunitySerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="titre", read_only=True)
    type = serializers.CharField(source="type_opportunite", read_only=True)
    status = serializers.CharField(source="statut", read_only=True)
    organization_name = serializers.CharField(source="organisation_nom", read_only=True)
    organization_email = serializers.EmailField(source="organisation.email", read_only=True, allow_null=True)
    location = serializers.CharField(source="ville", read_only=True)
    created_at = serializers.DateTimeField(source="date_creation", read_only=True)
    moderation = serializers.SerializerMethodField()

    class Meta:
        model = Opportunite
        fields = [
            "id",
            "title",
            "type",
            "status",
            "organization_name",
            "organization_email",
            "location",
            "created_at",
            "moderation",
        ]
        read_only_fields = fields

    def get_moderation(self, obj):
        extra_data = getattr(obj, "extra_data", None)
        if not isinstance(extra_data, dict):
            return {}
        moderation = extra_data.get("moderation")
        return moderation if isinstance(moderation, dict) else {}


class AdminOrganizationOpportunityDecisionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)


class AdminUserSerializer(serializers.ModelSerializer):
    last_login_at = serializers.DateTimeField(read_only=True, allow_null=True)
    provider = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "is_admin",
            "is_active",
            "is_suspended",
            "suspension_reason",
            "suspended_at",
            "account_type",
            "date_joined",
            "last_login_at",
            "provider",
        ]
        read_only_fields = fields

    def get_provider(self, obj):
        password = getattr(obj, "password", "") or ""
        return "PASSWORDLESS" if password.startswith("!") else "PASSWORD"


class AdminAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, allow_null=True)
    target_email = serializers.EmailField(source="target.email", read_only=True, allow_null=True)
    ip_address = serializers.SerializerMethodField()
    detail = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "actor_email",
            "target_email",
            "ip_address",
            "detail",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

    def get_ip_address(self, obj):
        return (obj.metadata or {}).get("ip_address", "")

    def get_detail(self, obj):
        metadata = obj.metadata or {}
        return (
            metadata.get("detail")
            or metadata.get("reason")
            or metadata.get("message")
            or ""
        )


class AdminUserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminAuditLogPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminUserFilter(django_filters.FilterSet):
    role = django_filters.CharFilter(method="filter_role")
    status = django_filters.CharFilter(method="filter_status")
    provider = django_filters.CharFilter(method="filter_provider")

    joined_after = django_filters.DateFilter(field_name="date_joined", lookup_expr="date__gte")
    joined_before = django_filters.DateFilter(field_name="date_joined", lookup_expr="date__lte")

    last_login_after = django_filters.DateFilter(field_name="last_login_at", lookup_expr="date__gte")
    last_login_before = django_filters.DateFilter(field_name="last_login_at", lookup_expr="date__lte")

    class Meta:
        model = User
        fields = []

    def filter_role(self, queryset, name, value):
        """
        Filter by role/account type.
        - admin: is_admin=True
        - candidat/candidate: account_type='candidate' AND is_admin=False
        - promoteur/organization: account_type='organization' AND is_admin=False
        - user (backward compat): same as 'all' (no filter)
        """
        normalized = (value or "").strip().lower()
        if normalized in {"admin"}:
            return queryset.filter(is_admin=True)
        if normalized in {"candidat", "candidate"}:
            return queryset.filter(is_admin=False, account_type='candidate')
        if normalized in {"promoteur", "organization"}:
            return queryset.filter(is_admin=False, account_type='organization')
        # Default: no filter, return all (includes 'user' for backward compat)
        return queryset

    def filter_status(self, queryset, name, value):
        """
        Filter by account status considering both is_active and is_suspended.
        - active: is_active=True AND is_suspended=False
        - suspended: is_suspended=True (regardless of is_active)
        """
        normalized = (value or "").strip().lower()
        if normalized in {"active"}:
            return queryset.filter(is_active=True, is_suspended=False)
        if normalized in {"suspended"}:
            return queryset.filter(is_suspended=True)
        return queryset

    def filter_provider(self, queryset, name, value):
        normalized = (value or "").strip().lower()
        if normalized in {"passwordless", "otp", "google"}:
            return queryset.filter(password__startswith="!")
        if normalized in {"password", "credentials"}:
            return queryset.exclude(password__startswith="!")
        return queryset


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


class AdminPendingOrganizationOpportunitiesView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = (
            Opportunite.objects
            .select_related("organisation", "source")
            .filter(statut=StatutOpportunite.PENDING_REVIEW)
            .filter(extra_data__published_by="organization")
            .order_by("-date_creation", "-id")
        )
        serializer = AdminPendingOrganizationOpportunitySerializer(queryset, many=True)
        return Response(serializer.data)


class AdminOrganizationOpportunityDecisionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk, decision):
        serializer = AdminOrganizationOpportunityDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = serializer.validated_data.get("note", "")
        opportunity = get_object_or_404(
            Opportunite.objects.select_related("organisation", "source"),
            pk=pk,
        )

        extra_data = opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {}
        if extra_data.get("published_by") != "organization":
            return Response(
                {"detail": "Only organization-published opportunities can be moderated here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if decision == "approve":
            return self._approve(request, opportunity, extra_data, note)
        if decision == "reject":
            return self._reject(request, opportunity, extra_data, note)

        return Response({"detail": "Unsupported moderation decision."}, status=status.HTTP_400_BAD_REQUEST)

    def _approve(self, request, opportunity, extra_data, note):
        if opportunity.statut == StatutOpportunite.ACTIVE:
            self._record_admin_decision(
                request=request,
                opportunity=opportunity,
                extra_data=extra_data,
                action="approved",
                note=note,
                before_status=opportunity.statut,
                after_status=opportunity.statut,
                audit_action=AuditLog.Action.APPROVE_ORG_OPPORTUNITY,
                message="Organization opportunity was already approved.",
            )
            return Response(
                {
                    "detail": "Opportunity is already approved.",
                    "opportunity": AdminOpportunitySerializer(opportunity).data,
                },
                status=status.HTTP_200_OK,
            )

        if opportunity.statut in {StatutOpportunite.ARCHIVEE, StatutOpportunite.REJECTED}:
            return Response(
                {"detail": "Archived or rejected opportunities cannot be approved from moderation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            before_status = opportunity.statut
            opportunity.statut = StatutOpportunite.ACTIVE
            admin_decision = self._record_admin_decision(
                request=request,
                opportunity=opportunity,
                extra_data=extra_data,
                action="approved",
                note=note,
                before_status=before_status,
                after_status=StatutOpportunite.ACTIVE,
                audit_action=AuditLog.Action.APPROVE_ORG_OPPORTUNITY,
                message="Organization opportunity approved for publication.",
            )
            opportunity.save(update_fields=["statut", "extra_data"])
            transaction.on_commit(
                lambda: send_organization_admin_decision_email_task.delay(
                    opportunity.pk,
                    "approved",
                    admin_decision["decided_at"],
                )
            )
        return Response(
            {
                "detail": "Opportunity approved and published.",
                "opportunity": AdminOpportunitySerializer(opportunity).data,
            },
            status=status.HTTP_200_OK,
        )

    def _reject(self, request, opportunity, extra_data, note):
        if opportunity.statut == StatutOpportunite.REJECTED:
            self._record_admin_decision(
                request=request,
                opportunity=opportunity,
                extra_data=extra_data,
                action="rejected",
                note=note,
                before_status=opportunity.statut,
                after_status=opportunity.statut,
                audit_action=AuditLog.Action.REJECT_ORG_OPPORTUNITY,
                message="Organization opportunity was already rejected.",
            )
            return Response(
                {
                    "detail": "Opportunity is already rejected.",
                    "opportunity": AdminOpportunitySerializer(opportunity).data,
                },
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            before_status = opportunity.statut
            opportunity.statut = StatutOpportunite.REJECTED
            admin_decision = self._record_admin_decision(
                request=request,
                opportunity=opportunity,
                extra_data=extra_data,
                action="rejected",
                note=note,
                before_status=before_status,
                after_status=StatutOpportunite.REJECTED,
                audit_action=AuditLog.Action.REJECT_ORG_OPPORTUNITY,
                message="Organization opportunity rejected.",
            )
            opportunity.save(update_fields=["statut", "extra_data"])
            transaction.on_commit(
                lambda: send_organization_admin_decision_email_task.delay(
                    opportunity.pk,
                    "rejected",
                    admin_decision["decided_at"],
                )
            )
        return Response(
            {
                "detail": "Opportunity rejected.",
                "opportunity": AdminOpportunitySerializer(opportunity).data,
            },
            status=status.HTTP_200_OK,
        )

    def _record_admin_decision(
        self,
        *,
        request,
        opportunity,
        extra_data,
        action,
        note,
        before_status,
        after_status,
        audit_action,
        message,
    ):
        moderation = extra_data.get("moderation")
        if not isinstance(moderation, dict):
            moderation = {}
            extra_data["moderation"] = moderation

        decided_at = timezone.now()
        admin_decision = {
            "action": action,
            "note": note,
            "admin_id": request.user.pk,
            "admin_email": request.user.email,
            "decided_at": decided_at.isoformat(),
            "before_status": before_status,
            "after_status": after_status,
        }
        moderation["admin_decision"] = admin_decision
        moderation["final_status"] = after_status
        if action == "approved":
            moderation["final_decision"] = "approved"
        elif action == "rejected":
            moderation["final_decision"] = "rejected"
        opportunity.extra_data = extra_data
        organization_profile = getattr(opportunity.organisation, "organization_profile", None)
        llm_moderation = moderation.get("llm")
        if not isinstance(llm_moderation, dict):
            llm_moderation = {}

        AuditLog.objects.create(
            actor=request.user,
            target=opportunity.organisation,
            action=audit_action,
            metadata={
                "message": message,
                "opportunity_id": opportunity.pk,
                "opportunity_title": opportunity.titre,
                "organization_email": opportunity.organisation.email if opportunity.organisation else "",
                "organization_name": (
                    getattr(organization_profile, "organization_name", "")
                    or opportunity.organisation_nom
                    or ""
                ),
                "organization_phone": getattr(organization_profile, "phone", "") or "",
                "organization_type": getattr(organization_profile, "organization_type", "") or "",
                "organization_website": getattr(organization_profile, "website", "") or "",
                "organization_contact_name": " ".join(
                    part
                    for part in [
                        getattr(organization_profile, "first_name", ""),
                        getattr(organization_profile, "last_name", ""),
                    ]
                    if part
                ),
                "before_status": before_status,
                "after_status": after_status,
                "decision": action,
                "note": note,
                "ai_category": llm_moderation.get("category", ""),
                "ai_decision": llm_moderation.get("decision", ""),
                "ai_confidence": llm_moderation.get("confidence"),
                "ai_explanation": llm_moderation.get("reason", ""),
            },
        )
        return admin_decision


class AdminUserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AdminUserPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AdminUserFilter
    search_fields = [
        "email",
        "first_name",
        "last_name",
        "username",
        "profil__nom",
        "profil__prenom",
    ]
    ordering_fields = ["email", "date_joined", "last_login_at"]
    ordering = ["-date_joined", "-id"]

    def _client_ip(self):
        forwarded = self.request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.request.META.get("REMOTE_ADDR", "")

    def _blacklist_user_refresh_tokens(self, user):
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)

    def _audit(self, *, action, target, metadata=None):
        payload = {
            "ip_address": self._client_ip(),
            "user_agent": self.request.META.get("HTTP_USER_AGENT", ""),
            **(metadata or {}),
        }
        AuditLog.objects.create(
            actor=self.request.user,
            target=target,
            action=action,
            metadata=payload,
        )

    def get_queryset(self):
        last_login_subquery = (
            LoginEvent.objects.filter(user_id=OuterRef("pk"))
            .order_by("-created_at")
            .values("created_at")[:1]
        )
        return (
            User.objects.all()
            .annotate(
                last_login_at=Subquery(
                    last_login_subquery,
                    output_field=DateTimeField(),
                )
            )
            .order_by("-date_joined", "-id")
        )

    @action(detail=True, methods=["post"], url_path="toggle-admin")
    def toggle_admin(self, request, pk=None):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot modify your own admin role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        before = user.is_admin
        user.is_admin = not user.is_admin
        user.save(update_fields=["is_admin"])
        self._blacklist_user_refresh_tokens(user)
        self._audit(
            action=AuditLog.Action.TOGGLE_ADMIN,
            target=user,
            metadata={
                "before_is_admin": before,
                "after_is_admin": user.is_admin,
                "message": "Admin role changed; refresh tokens revoked.",
            },
        )
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
        self._blacklist_user_refresh_tokens(user)
        self._audit(
            action=AuditLog.Action.TOGGLE_ACTIVE,
            target=user,
            metadata={
                "after_is_active": user.is_active,
                "message": "Active status changed; refresh tokens revoked.",
            },
        )
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=["post"], url_path="suspend")
    def suspend_user(self, request, pk=None):
        """
        Suspend a user account for moderation reasons.
        POST /admin/users/{id}/suspend/ 
        Body: {"reason": "spam|abuse|fraud|other", "detail": "optional context"}
        """
        # Validate input data
        serializer = UserSuspensionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        user = self.get_object()
        reason = serializer.validated_data.get("reason")
        detail = serializer.validated_data.get("detail", "")

        # Guard: cannot suspend self
        if user.pk == request.user.pk:
            return Response(
                {"detail": "Vous ne pouvez pas suspendre votre propre compte administrateur."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Guard: cannot suspend last active admin
        if user.is_admin and user.is_active:
            other_active_admins = (
                User.objects.filter(is_admin=True, is_active=True)
                .exclude(pk=user.pk)
                .exists()
            )
            if not other_active_admins:
                return Response(
                    {"detail": "Impossible de suspendre le dernier administrateur actif."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Suspend user
        from django.utils import timezone
        user.is_suspended = True
        user.suspension_reason = reason
        user.suspended_at = timezone.now()
        user.save(update_fields=["is_suspended", "suspension_reason", "suspended_at"])
        self._blacklist_user_refresh_tokens(user)
        self._audit(
            action=AuditLog.Action.SUSPEND,
            target=user,
            metadata={
                "reason": reason,
                "detail": detail,
                "message": "User suspended; refresh tokens revoked.",
            },
        )

        return Response(self.get_serializer(user).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reactivate")
    def reactivate_user(self, request, pk=None):
        """
        Reactivate a suspended user account.
        POST /admin/users/{id}/reactivate/
        """
        user = self.get_object()

        # Reactivate user
        user.is_suspended = False
        user.suspension_reason = ""
        user.suspended_at = None
        user.save(update_fields=["is_suspended", "suspension_reason", "suspended_at"])
        self._blacklist_user_refresh_tokens(user)
        self._audit(
            action=AuditLog.Action.REACTIVATE,
            target=user,
            metadata={
                "message": "User reactivated; refresh tokens revoked.",
            },
        )

        return Response(self.get_serializer(user).data, status=status.HTTP_200_OK)


class AdminAuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminAuditLogSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AdminAuditLogPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at", "action"]
    ordering = ["-created_at", "-id"]

    class AuditLogFilter(django_filters.FilterSet):
        action = django_filters.CharFilter(method="filter_action")

        class Meta:
            model = AuditLog
            fields = []

        def filter_action(self, queryset, name, value):
            normalized = (value or "").strip().upper()
            allowed = {choice.value for choice in AuditLog.Action}
            if normalized in allowed:
                return queryset.filter(action=normalized)
            return queryset

    filterset_class = AuditLogFilter

    def get_queryset(self):
        return AuditLog.objects.select_related("actor", "target").order_by("-created_at", "-id")

    def _audit_export_rows(self, queryset):
        for entry in queryset[:5000]:
            metadata = entry.metadata or {}
            yield {
                "timestamp": timezone.localtime(entry.created_at).strftime("%Y-%m-%d %H:%M"),
                "action": entry.action,
                "target": entry.target.email if entry.target else "",
                "admin": entry.actor.email if entry.actor else "",
                "detail": metadata.get("detail") or metadata.get("reason") or metadata.get("message") or "",
            }

    def _escape_pdf_text(self, value):
        text = str(value or "").replace("\r", " ").replace("\n", " ")
        text = text.encode("ascii", "replace").decode("ascii")
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _build_pdf(self, rows):
        columns = [
            ("Date", 92),
            ("Action", 92),
            ("User email", 170),
            ("Admin email", 170),
            ("Details", 245),
        ]
        row_height = 18
        rows_per_page = 22
        pages = [rows[index:index + rows_per_page] for index in range(0, len(rows), rows_per_page)] or [[]]
        objects = [
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids ["
            + " ".join(f"{3 + page_index * 2} 0 R" for page_index in range(len(pages)))
            + f"] /Count {len(pages)} >>",
        ]

        for page_index, page_lines in enumerate(pages):
            page_object_id = 3 + page_index * 2
            content_object_id = page_object_id + 1
            content_lines = [
                "0.96 0.98 1 rg 0 535 842 60 re f",
                "0.08 0.17 0.30 rg 0 535 842 60 re f",
                "1 1 1 rg BT /F2 20 Tf 36 564 Td (BidWise) Tj ET",
                "1 1 1 rg BT /F1 10 Tf 36 548 Td (Admin audit log export) Tj ET",
                f"1 1 1 rg BT /F1 9 Tf 650 564 Td (Page {page_index + 1} of {len(pages)}) Tj ET",
                f"1 1 1 rg BT /F1 9 Tf 650 548 Td (Generated {self._escape_pdf_text(timezone.localtime(now()).strftime('%Y-%m-%d %H:%M'))}) Tj ET",
                "0.20 0.25 0.33 rg BT /F1 9 Tf 36 514 Td "
                f"({self._escape_pdf_text(f'{len(rows)} filtered audit events exported. Limit: 5000 most recent events.')}) Tj ET",
                "0.93 0.95 0.97 rg 36 484 770 24 re f",
                "0.72 0.76 0.82 RG 36 484 770 24 re S",
            ]

            x = 44
            for label, width in columns:
                content_lines.append(
                    f"0.16 0.20 0.28 rg BT /F2 8 Tf {x} 493 Td "
                    f"({self._escape_pdf_text(label)}) Tj ET"
                )
                x += width

            y = 466
            for row_index, row in enumerate(page_lines):
                fill = "0.99 0.99 1 rg" if row_index % 2 == 0 else "1 1 1 rg"
                content_lines.append(f"{fill} 36 {y - 5} 770 {row_height} re f")
                content_lines.append(f"0.90 0.92 0.95 RG 36 {y - 5} 770 {row_height} re S")
                values = [
                    row["timestamp"],
                    row["action"],
                    row["target"] or "Deleted user",
                    row["admin"] or "Unknown admin",
                    row["detail"] or "-",
                ]
                x = 44
                for value, (_, width) in zip(values, columns):
                    max_chars = max(int(width / 4.6), 8)
                    text = str(value)
                    if len(text) > max_chars:
                        text = text[:max_chars - 3] + "..."
                    content_lines.append(
                        f"0.20 0.25 0.33 rg BT /F1 7 Tf {x} {y} Td "
                        f"({self._escape_pdf_text(text)}) Tj ET"
                    )
                    x += width
                y -= row_height

            content = "\n".join(content_lines)
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] "
                f"/Resources << /Font << /F1 {3 + len(pages) * 2} 0 R "
                f"/F2 {4 + len(pages) * 2} 0 R >> >> "
                f"/Contents {content_object_id} 0 R >>"
            )
            objects.append(f"<< /Length {len(content.encode('utf-8'))} >>\nstream\n{content}\nendstream")

        objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for object_index, body in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{object_index} 0 obj\n{body}\nendobj\n".encode("utf-8"))
        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
        pdf.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("utf-8")
        )
        return bytes(pdf)

    @action(detail=False, methods=["get"], url_path="export")
    def export_csv(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="bidwise-admin-audit-log.csv"'
        writer = csv.writer(response)
        writer.writerow(["timestamp", "action", "target_email", "admin_email", "detail"])
        for row in self._audit_export_rows(queryset):
            writer.writerow([
                row["timestamp"],
                row["action"],
                row["target"],
                row["admin"],
                row["detail"],
            ])
        return response

    @action(detail=False, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        pdf = self._build_pdf(list(self._audit_export_rows(queryset)))
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="bidwise-admin-audit-log.pdf"'
        return response

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

        if user.is_suspended:
            return Response(
                {"detail": "Admin account is suspended."},
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
            "inspect_error": True,
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
        "inspect_error": False,
    }


def _derive_pipeline_health_status(*, latest_run, celery_snapshot, alerts, pipeline_lag):
    """
    Build a single trustworthy pipeline status from live runtime signals.

    Priority order matters:
    1. `failed` when a recent hard failure is known.
    2. `degraded` when supervision, backlog, or freshness is impaired.
    3. `running` when ingestion is actively progressing without blocking issues.
    4. `healthy` otherwise.

    This keeps the admin dashboard grounded in operational state instead of
    showing "idle" while the latest run has actually failed or gone stale.
    """

    alerts = alerts or []
    celery_snapshot = celery_snapshot or {}
    pipeline_lag = pipeline_lag or {}

    has_critical_alert = any(alert.get("severity") == "CRITICAL" for alert in alerts)
    has_warning_alert = any(alert.get("severity") == "WARNING" for alert in alerts)
    latest_run_failed = bool(latest_run and latest_run.status == PipelineRunStatus.FAILED)
    latest_run_stale = bool(latest_run and latest_run.is_stale)
    backlog_detected = bool(pipeline_lag.get("backlog_detected"))
    pipeline_running = bool(celery_snapshot.get("pipeline_running"))
    inspect_error = bool(celery_snapshot.get("inspect_error"))
    workers = int(celery_snapshot.get("workers") or 0)

    if has_critical_alert:
        return {
            "status": "failed",
            "reason": "critical_alert",
            "detail": "Critical pipeline alerts are active and need immediate review.",
        }

    if latest_run_failed:
        return {
            "status": "failed",
            "reason": "last_run_failed",
            "detail": "The latest pipeline run failed and requires investigation.",
        }

    if inspect_error:
        return {
            "status": "degraded",
            "reason": "celery_inspect_unavailable",
            "detail": "Celery supervision is temporarily unavailable, so worker health cannot be fully confirmed.",
        }

    if workers <= 0:
        return {
            "status": "degraded",
            "reason": "no_workers",
            "detail": "No active Celery workers were detected for the ingestion pipeline.",
        }

    if latest_run_stale:
        return {
            "status": "degraded",
            "reason": "stale_run",
            "detail": "The latest pipeline run is stale and may no longer be progressing normally.",
        }

    if backlog_detected:
        return {
            "status": "degraded",
            "reason": "pipeline_backlog",
            "detail": "Raw opportunity backlog is still pending after ingestion and should be reviewed.",
        }

    if has_warning_alert:
        return {
            "status": "degraded",
            "reason": "warning_alert",
            "detail": "Warning-level monitoring alerts are active and should be checked.",
        }

    if pipeline_running:
        return {
            "status": "running",
            "reason": "pipeline_running",
            "detail": "Ingestion is currently running and workers are available.",
        }

    return {
        "status": "healthy",
        "reason": "nominal",
        "detail": "Sources, workers, and freshness checks are within expected ranges.",
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


def _summarize_error_message(message):
    value = " ".join(str(message or "").split()).strip()
    if not value:
        return ""
    if len(value) <= 180:
        return value
    return f"{value[:177].rstrip()}..."


def _summarize_source_issue(active_alert):
    if not active_alert:
        return {
            "status": "healthy",
            "summary": "",
            "detail": "",
        }

    title = str(active_alert.get("title") or "").strip()
    details = _summarize_error_message(active_alert.get("details"))
    severity = str(active_alert.get("severity") or "").upper()

    if title and details:
        summary = f"{title}: {details}"
    else:
        summary = title or details

    return {
        "status": "failed" if severity == "CRITICAL" else "warning",
        "summary": summary,
        "detail": details,
    }


def _derive_source_operational_status(*, source_name, running_sources, schedule_state):
    if source_name in running_sources:
        return {
            "status": "running",
            "detail": "Collection is currently running.",
        }

    latest_run_status = schedule_state.get("latest_run_status")
    if schedule_state.get("is_running_stale"):
        return {
            "status": "failed",
            "detail": "The active run exceeded its maximum expected duration.",
        }

    if latest_run_status == PipelineRunStatus.FAILED:
        return {
            "status": "failed",
            "detail": "The latest run failed and needs investigation.",
        }

    if schedule_state.get("is_stale"):
        return {
            "status": "degraded",
            "detail": "No recent fresh opportunities were detected for this source.",
        }

    if not schedule_state.get("last_run_at"):
        return {
            "status": "degraded",
            "detail": "No pipeline run has been recorded for this source yet.",
        }

    return {
        "status": "healthy",
        "detail": "Recent runs completed within the expected freshness window.",
    }


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
    change_rate = ((total_created + total_updated) / total_processed) * 100 if total_processed else 0.0
    total_runs = aggregates.get("total_runs") or 0
    successful_runs = aggregates.get("success_runs") or 0
    run_success_rate = (successful_runs / total_runs) * 100 if total_runs else 0.0

    return {
        "total_runs": total_runs,
        "success_runs": successful_runs,
        "failed_runs": aggregates.get("failed_runs") or 0,
        "total_processed": total_processed,
        "total_created": total_created,
        "total_updated": total_updated,
        "total_failed_pages": total_failed_pages,
        "change_rate": change_rate,
        "run_success_rate": run_success_rate,
        # Backward compatibility for existing consumers; prefer `change_rate`.
        "success_rate": change_rate,
        "avg_duration": aggregates.get("avg_duration") or 0.0,
    }


def get_source_monitoring(running_sources=None, alerts=None):
    running_sources = set(running_sources or [])
    alerts_by_source = {}
    for alert in alerts or []:
        source_key = alert.get("source")
        if not source_key:
            continue
        current = alerts_by_source.get(source_key)
        if current is None:
            alerts_by_source[source_key] = alert
            continue
        current_rank = 2 if str(current.get("severity") or "").upper() == "CRITICAL" else 1
        incoming_rank = 2 if str(alert.get("severity") or "").upper() == "CRITICAL" else 1
        if incoming_rank > current_rank:
            alerts_by_source[source_key] = alert

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
        active_alert = alerts_by_source.get(source)
        schedule_state = get_source_schedule_state(source)
        source_health = _derive_source_operational_status(
            source_name=source,
            running_sources=running_sources,
            schedule_state=schedule_state,
        )
        issue_state = _summarize_source_issue(active_alert)
        latest_run_status = schedule_state.get("latest_run_status")
        raw_last_error_message = row.get("last_error_message")
        current_error_summary = (
            _summarize_error_message(raw_last_error_message)
            if latest_run_status == PipelineRunStatus.FAILED or source_health["status"] == "failed"
            else ""
        )
        current_issue_summary = issue_state["summary"] or current_error_summary
        current_issue_status = issue_state["status"] if issue_state["summary"] else (
            "failed" if current_error_summary else "healthy"
        )
        total_processed = row.get("total_processed") or 0
        total_created = row.get("total_created") or 0
        total_updated = row.get("total_updated") or 0
        change_rate = (
            ((total_created + total_updated) / total_processed) * 100
            if total_processed
            else 0.0
        )
        total_runs = row.get("total_runs") or 0
        successful_runs = row.get("success_runs") or 0
        run_success_rate = (successful_runs / total_runs) * 100 if total_runs else 0.0

        sources.append(
            {
                "source": source,
                "total_runs": total_runs,
                "success_runs": successful_runs,
                "failed_runs": row.get("failed_runs") or 0,
                "total_processed": total_processed,
                "total_created": total_created,
                "total_updated": total_updated,
                "total_failed_pages": row.get("total_failed_pages") or 0,
                "avg_duration": row.get("avg_duration") or 0.0,
                "last_run": row.get("last_run"),
                "last_activity_at": schedule_state.get("last_activity_at"),
                "last_error_message": raw_last_error_message,
                "last_error_summary": current_error_summary,
                "current_issue_status": current_issue_status,
                "current_issue_summary": current_issue_summary,
                "change_rate": change_rate,
                "run_success_rate": run_success_rate,
                # Backward compatibility for existing consumers; prefer `change_rate`.
                "success_rate": change_rate,
                "is_running": source in running_sources,
                "operational_status": source_health["status"],
                "operational_detail": source_health["detail"],
                "latest_run_status": latest_run_status,
                "is_stale": bool(schedule_state.get("is_stale")),
                "is_running_stale": bool(schedule_state.get("is_running_stale")),
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


def _count_since(queryset, field_name, start_date):
    return queryset.filter(**{f"{field_name}__date__gte": start_date}).count()


def _count_today(queryset, field_name, today):
    return queryset.filter(**{f"{field_name}__date": today}).count()


def _serialize_status_counts(queryset, field_name):
    return {
        row[field_name]: row["count"]
        for row in queryset.values(field_name).annotate(count=Count("id")).order_by(field_name)
    }


def _daily_series(queryset, field_name, start_date, end_date):
    rows = (
        queryset.filter(**{f"{field_name}__date__gte": start_date, f"{field_name}__date__lte": end_date})
        .annotate(day=TruncDate(field_name))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    counts_by_day = {row["day"]: row["count"] for row in rows}
    days_count = (end_date - start_date).days + 1

    return [
        {
            "date": (start_date + timedelta(days=offset)).isoformat(),
            "count": counts_by_day.get(start_date + timedelta(days=offset), 0),
        }
        for offset in range(days_count)
    ]


def get_platform_statistics():
    today = now().date()
    start_7_days = today - timedelta(days=6)
    start_30_days = today - timedelta(days=29)
    users = User.objects.all()
    opportunities = Opportunite.objects.exclude(removed_source_q("source__nom"))
    applications = Candidature.objects.all()

    total_users = users.count()
    total_opportunities = opportunities.count()
    total_applications = applications.count()
    non_admin_users = users.filter(is_admin=False)
    active_users = users.filter(is_active=True, is_suspended=False)
    candidate_users = non_admin_users.filter(account_type="candidate")
    organization_users = non_admin_users.filter(account_type="organization")
    active_opportunities = opportunities.filter(statut=StatutOpportunite.ACTIVE)
    active_opportunities_count = active_opportunities.count()

    return {
        "generated_at": now(),
        "users": {
            "total": total_users,
            "active": active_users.count(),
            "suspended": users.filter(is_suspended=True).count(),
            "admins": users.filter(is_admin=True).count(),
            "candidates": candidate_users.count(),
            "organizations": organization_users.count(),
            "new_today": _count_today(users, "date_joined", today),
            "new_7_days": _count_since(users, "date_joined", start_7_days),
            "new_30_days": _count_since(users, "date_joined", start_30_days),
        },
        "applications": {
            "total": total_applications,
            "today": _count_today(applications, "date_creation", today),
            "last_7_days": _count_since(applications, "date_creation", start_7_days),
            "last_30_days": _count_since(applications, "date_creation", start_30_days),
            "by_status": _serialize_status_counts(applications, "statut"),
        },
        "opportunities": {
            "total": total_opportunities,
            "active": active_opportunities_count,
            "expired": opportunities.filter(statut=StatutOpportunite.EXPIREE).count(),
            "archived": opportunities.filter(statut=StatutOpportunite.ARCHIVEE).count(),
            "rejected": opportunities.filter(statut=StatutOpportunite.REJECTED).count(),
            "created_today": _count_today(opportunities, "date_creation", today),
            "created_7_days": _count_since(opportunities, "date_creation", start_7_days),
            "created_30_days": _count_since(opportunities, "date_creation", start_30_days),
            "by_type": _serialize_status_counts(opportunities, "type_opportunite"),
            "by_status": _serialize_status_counts(opportunities, "statut"),
        },
        "conversion": {
            "application_rate": (total_applications / total_opportunities) * 100 if total_opportunities else 0.0,
            "applications_per_user": total_applications / total_users if total_users else 0.0,
            "applications_per_active_opportunity": (
                total_applications / active_opportunities_count if active_opportunities_count else 0.0
            ),
        },
        "growth": {
            "days": 30,
            "users": _daily_series(users, "date_joined", start_30_days, today),
            "applications": _daily_series(applications, "date_creation", start_30_days, today),
            "opportunities": _daily_series(opportunities, "date_creation", start_30_days, today),
        },
    }


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _counter_top_value(counter):
    if not counter:
        return ""
    return counter.most_common(1)[0][0]


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        return parse_datetime(str(value))
    except (TypeError, ValueError):
        return None


def get_ai_supervision_snapshot():
    """
    Build a conservative AI supervision snapshot from persisted data only.

    This intentionally avoids synthetic "accuracy" claims. Every metric below
    is backed by stored moderation metadata, enrichment payloads, resume
    semantic fields, or embedding coverage already present in the database.
    """

    organization_opportunities = (
        Opportunite.objects.filter(extra_data__published_by="organization")
        .only("id", "extra_data", "statut", "date_modification")
        .order_by("-date_modification", "-id")
    )
    moderation_total = organization_opportunities.count()
    moderation_processed = 0
    moderation_skipped = 0
    moderation_fallbacks = 0
    moderation_admin_reviewed = 0
    moderation_admin_overrides = 0
    moderation_confidence_sum = 0.0
    moderation_confidence_count = 0
    moderation_decisions = Counter()
    moderation_categories = Counter()
    moderation_providers = Counter()
    moderation_models = Counter()
    moderation_last_updated = None

    for opportunity in organization_opportunities:
        extra_data = getattr(opportunity, "extra_data", {}) or {}
        if not isinstance(extra_data, dict):
            continue
        moderation = extra_data.get("moderation")
        if not isinstance(moderation, dict):
            continue
        llm = moderation.get("llm")
        if not isinstance(llm, dict):
            continue

        moderation_processed += 1
        moderation_decisions[str(llm.get("decision") or "").strip().lower() or "unknown"] += 1
        moderation_categories[str(llm.get("category") or "").strip().lower() or "unknown"] += 1

        provider = str(llm.get("provider") or "").strip()
        model = str(llm.get("model") or "").strip()
        if provider:
            moderation_providers[provider] += 1
        if model:
            moderation_models[model] += 1

        if llm.get("confidence") is not None:
            moderation_confidence_sum += _safe_float(llm.get("confidence"))
            moderation_confidence_count += 1

        if bool(llm.get("skipped")):
            moderation_skipped += 1
        if str(llm.get("error") or "").strip():
            moderation_fallbacks += 1

        admin_decision = moderation.get("admin_decision")
        if isinstance(admin_decision, dict) and admin_decision.get("action"):
            moderation_admin_reviewed += 1
            admin_action = str(admin_decision.get("action") or "").strip().lower()
            admin_mapped = "approved" if admin_action == "approved" else "rejected" if admin_action == "rejected" else ""
            llm_decision = str(llm.get("decision") or "").strip().lower()
            if admin_mapped and llm_decision and admin_mapped != llm_decision:
                moderation_admin_overrides += 1

            decided_at = _parse_iso_datetime(admin_decision.get("decided_at"))
            if decided_at and (moderation_last_updated is None or decided_at > moderation_last_updated):
                moderation_last_updated = decided_at

        updated_at = getattr(opportunity, "date_modification", None)
        if updated_at and (moderation_last_updated is None or updated_at > moderation_last_updated):
            moderation_last_updated = updated_at

    opportunity_queryset = (
        Opportunite.objects.exclude(removed_source_q("source__nom"))
        .only("id", "extra_data", "date_modification")
        .order_by("-date_modification", "-id")
    )
    enrichment_total = opportunity_queryset.count()
    enrichment_processed = 0
    enrichment_applied_to_skills = 0
    enrichment_with_warnings = 0
    enrichment_confidence_sum = 0.0
    enrichment_confidence_count = 0
    enrichment_providers = Counter()
    enrichment_models = Counter()
    enrichment_last_updated = None

    for opportunity in opportunity_queryset:
        extra_data = getattr(opportunity, "extra_data", {}) or {}
        if not isinstance(extra_data, dict):
            continue
        enrichment = extra_data.get("llm_enrichment")
        if not isinstance(enrichment, dict):
            continue

        enrichment_processed += 1
        if bool(enrichment.get("applied_to_skills")):
            enrichment_applied_to_skills += 1
        if isinstance(enrichment.get("warnings"), list) and enrichment.get("warnings"):
            enrichment_with_warnings += 1

        if enrichment.get("confidence") is not None:
            enrichment_confidence_sum += _safe_float(enrichment.get("confidence"))
            enrichment_confidence_count += 1

        provider = str(enrichment.get("provider") or "").strip()
        model = str(enrichment.get("model") or "").strip()
        if provider:
            enrichment_providers[provider] += 1
        if model:
            enrichment_models[model] += 1

        updated_at = _parse_iso_datetime(enrichment.get("updated_at")) or getattr(opportunity, "date_modification", None)
        if updated_at and (enrichment_last_updated is None or updated_at > enrichment_last_updated):
            enrichment_last_updated = updated_at

    resume_queryset = (
        ProfileResume.objects.filter(is_active=True)
        .only(
            "id",
            "semantic_resume_status",
            "semantic_resume_confidence",
            "semantic_resume_updated_at",
            "semantic_resume_error",
            "semantic_resume_metadata",
        )
        .order_by("-semantic_resume_updated_at", "-id")
    )
    resume_total = resume_queryset.count()
    resume_statuses = Counter()
    resume_confidence_sum = 0.0
    resume_confidence_count = 0
    resume_providers = Counter()
    resume_models = Counter()
    resume_last_updated = None
    resume_last_error = ""
    resume_last_error_at = None

    for resume in resume_queryset:
        status_value = str(getattr(resume, "semantic_resume_status", "") or "PENDING").strip().upper()
        resume_statuses[status_value or "UNKNOWN"] += 1

        if status_value == "SUCCEEDED":
            resume_confidence_sum += _safe_float(getattr(resume, "semantic_resume_confidence", 0.0))
            resume_confidence_count += 1

        metadata = getattr(resume, "semantic_resume_metadata", {}) or {}
        if isinstance(metadata, dict):
            llm_enrichment = metadata.get("llm_enrichment")
            if isinstance(llm_enrichment, dict):
                provider = str(llm_enrichment.get("provider") or "").strip()
                model = str(llm_enrichment.get("model") or "").strip()
                if provider:
                    resume_providers[provider] += 1
                if model:
                    resume_models[model] += 1

        updated_at = getattr(resume, "semantic_resume_updated_at", None)
        if updated_at and (resume_last_updated is None or updated_at > resume_last_updated):
            resume_last_updated = updated_at

        error = str(getattr(resume, "semantic_resume_error", "") or "").strip()
        if error and updated_at and (resume_last_error_at is None or updated_at > resume_last_error_at):
            resume_last_error_at = updated_at
            resume_last_error = error

    profile_queryset = Profil.objects.only(
        "id",
        "embedding_updated_at",
        "jobbert_embedding",
        "jobbert_embedding_updated_at",
    )
    profile_total = profile_queryset.count()
    profile_embeddings = 0
    profile_jobbert_embeddings = 0
    for profile in profile_queryset:
        if getattr(profile, "embedding_updated_at", None):
            profile_embeddings += 1
        if getattr(profile, "jobbert_embedding_updated_at", None) or getattr(profile, "jobbert_embedding", None):
            profile_jobbert_embeddings += 1

    recommendation_queryset = Opportunite.objects.exclude(removed_source_q("source__nom")).only(
        "id",
        "embedding_vector",
        "embedding_vector_pg",
        "jobbert_embedding_vector",
        "jobbert_embedding_updated_at",
    )
    recommendation_total = recommendation_queryset.count()
    opportunity_embeddings = 0
    opportunity_pg_embeddings = 0
    opportunity_jobbert_embeddings = 0
    for opportunity in recommendation_queryset:
        if getattr(opportunity, "embedding_vector", None) is not None:
            opportunity_embeddings += 1
        if getattr(opportunity, "embedding_vector_pg", None) is not None:
            opportunity_pg_embeddings += 1
        if (
            getattr(opportunity, "jobbert_embedding_updated_at", None) is not None
            or getattr(opportunity, "jobbert_embedding_vector", None) is not None
        ):
            opportunity_jobbert_embeddings += 1

    return {
        "modules": {
            "moderation": {
                "module": "Moderation AI",
                "total": moderation_total,
                "processed": moderation_processed,
                "coverage": (moderation_processed / moderation_total * 100) if moderation_total else 0.0,
                "approved": int(moderation_decisions.get("approved", 0)),
                "pending_review": int(moderation_decisions.get("pending_review", 0)),
                "rejected": int(moderation_decisions.get("rejected", 0)),
                "skipped": moderation_skipped,
                "fallbacks": moderation_fallbacks,
                "admin_reviewed": moderation_admin_reviewed,
                "admin_overrides": moderation_admin_overrides,
                "override_rate": (
                    moderation_admin_overrides / moderation_admin_reviewed * 100
                    if moderation_admin_reviewed
                    else 0.0
                ),
                "average_confidence": (
                    moderation_confidence_sum / moderation_confidence_count
                    if moderation_confidence_count
                    else 0.0
                ),
                "top_category": _counter_top_value(moderation_categories),
                "provider": _counter_top_value(moderation_providers),
                "model": _counter_top_value(moderation_models),
                "last_updated_at": moderation_last_updated,
                "current_issue": "Fallback moderation results were stored for some offers." if moderation_fallbacks else "",
            },
            "opportunity_enrichment": {
                "module": "Opportunity Enrichment",
                "total": enrichment_total,
                "processed": enrichment_processed,
                "coverage": (enrichment_processed / enrichment_total * 100) if enrichment_total else 0.0,
                "applied_to_skills": enrichment_applied_to_skills,
                "with_warnings": enrichment_with_warnings,
                "average_confidence": (
                    enrichment_confidence_sum / enrichment_confidence_count
                    if enrichment_confidence_count
                    else 0.0
                ),
                "provider": _counter_top_value(enrichment_providers),
                "model": _counter_top_value(enrichment_models),
                "last_updated_at": enrichment_last_updated,
                "current_issue": "Some LLM enrichments produced warnings." if enrichment_with_warnings else "",
            },
            "resume_semantic": {
                "module": "Resume Semantic AI",
                "total": resume_total,
                "processed": int(resume_statuses.get("SUCCEEDED", 0)),
                "coverage": (resume_statuses.get("SUCCEEDED", 0) / resume_total * 100) if resume_total else 0.0,
                "succeeded": int(resume_statuses.get("SUCCEEDED", 0)),
                "failed": int(resume_statuses.get("FAILED", 0)),
                "empty": int(resume_statuses.get("EMPTY", 0)),
                "pending": int(resume_statuses.get("PENDING", 0) + resume_statuses.get("PROCESSING", 0)),
                "skipped": int(resume_statuses.get("SKIPPED", 0)),
                "average_confidence": (
                    resume_confidence_sum / resume_confidence_count
                    if resume_confidence_count
                    else 0.0
                ),
                "provider": _counter_top_value(resume_providers),
                "model": _counter_top_value(resume_models),
                "last_updated_at": resume_last_updated,
                "current_issue": resume_last_error,
            },
            "recommendation_readiness": {
                "module": "Recommendation Readiness",
                "profile_total": profile_total,
                "profile_embeddings": profile_embeddings,
                "profile_jobbert_embeddings": profile_jobbert_embeddings,
                "profile_coverage": (profile_embeddings / profile_total * 100) if profile_total else 0.0,
                "opportunity_total": recommendation_total,
                "opportunity_embeddings": opportunity_embeddings,
                "opportunity_pg_embeddings": opportunity_pg_embeddings,
                "opportunity_jobbert_embeddings": opportunity_jobbert_embeddings,
                "opportunity_coverage": (
                    opportunity_embeddings / recommendation_total * 100
                    if recommendation_total
                    else 0.0
                ),
                "current_issue": (
                    "Some profiles or opportunities are still missing embeddings."
                    if profile_embeddings < profile_total or opportunity_embeddings < recommendation_total
                    else ""
                ),
            },
        }
    }


def _serialize_pipeline_run(run):
    processed = _run_total(run, "total_processed", "processed_count")
    created = _run_total(run, "total_created", "created_count")
    updated = _run_total(run, "total_updated", "updated_count")
    change_rate = ((created + updated) / processed * 100) if processed else 0.0

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
        "change_rate": change_rate,
        # Backward compatibility for existing consumers; prefer `change_rate`.
        "success_rate": change_rate,
    }


class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        view = (request.query_params.get("view") or "").strip().lower()
        if view in {"platform", "global"}:
            return Response({"platform": get_platform_statistics()})

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
        embedding_monitoring = get_embedding_monitoring()
        logo_monitoring = get_logo_monitoring()
        pipeline_lag = get_pipeline_lag_monitoring()
        ai_supervision = get_ai_supervision_snapshot()
        platform_statistics = get_platform_statistics()
        alerts = collect_pipeline_anomalies()
        monitoring_sources = get_source_monitoring(
            celery.get("running_sources", []),
            alerts=alerts,
        )
        pipeline_health = _derive_pipeline_health_status(
            latest_run=latest_run,
            celery_snapshot=celery,
            alerts=alerts,
            pipeline_lag=pipeline_lag,
        )
        latest_processed = _run_total(latest_run, "total_processed", "processed_count") if latest_run else 0
        latest_created = _run_total(latest_run, "total_created", "created_count") if latest_run else 0
        latest_updated = _run_total(latest_run, "total_updated", "updated_count") if latest_run else 0
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
                    "change_rate": pipeline_stats["change_rate"],
                    "run_success_rate": pipeline_stats["run_success_rate"],
                    "success_rate": pipeline_stats["success_rate"],
                    "logo_coverage": logo_monitoring["coverage"],
                },
                "pipeline": {
                    "last_run": latest_run.finished_at if latest_run else None,
                    "status": pipeline_health["status"],
                    "status_reason": pipeline_health["reason"],
                    "status_detail": pipeline_health["detail"],
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
                "platform": platform_statistics,
                "ai_supervision": ai_supervision,
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
