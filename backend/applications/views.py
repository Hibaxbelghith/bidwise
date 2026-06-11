import secrets
from pathlib import Path

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opportunities.models import Opportunite, StatutOpportunite, TypeOpportunite
from opportunities.tasks import (
    notify_candidate_application_submitted_task,
    notify_organization_new_application_task,
)
from users.models import Utilisateur
from users.storage import ProfileResumeStorage

from .models import Candidature, StatutSuiviCandidature
from .permissions import IsOwnerCandidature
from .serializers import (
    CandidateApplicationListSerializer,
    CandidatureSerializer,
    CoverLetterUploadSerializer,
    ExternalApplicationStatusUpdateSerializer,
    InternalApplicationCreateSerializer,
    OrganizationApplicationRestoreSerializer,
    OrganizationCandidateApplicationProfileSerializer,
    OrganizationReceivedApplicationSerializer,
    OrganizationAllApplicationsSerializer,
)


ORGANIZATION_SOURCE_NAME = "BidWise Organizations"
INTERNAL_APPLICATION_TYPES = {
    TypeOpportunite.EMPLOI,
    TypeOpportunite.STAGE,
    TypeOpportunite.SAISONNIER,
}
CANDIDATE_VISIBLE_APPLICATION_STATUSES = {
    StatutSuiviCandidature.SUBMITTED,
    StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
    StatutSuiviCandidature.SHORTLISTED,
    StatutSuiviCandidature.REJECTED,
    StatutSuiviCandidature.WITHDRAWN,
    StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED,
    StatutSuiviCandidature.EXTERNAL_REMIND_LATER,
}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_candidate_applications(request):
    if request.user.account_type != Utilisateur.AccountType.CANDIDATE:
        return Response(
            {"detail": "Only candidate accounts can view their applications."},
            status=status.HTTP_403_FORBIDDEN,
        )

    applications = (
        Candidature.objects.filter(
            candidat=request.user,
            statut__in=CANDIDATE_VISIBLE_APPLICATION_STATUSES,
        )
        .select_related("opportunite")
        .order_by(
            F("submitted_at").desc(nulls_last=True),
            "-date_creation",
            "-id",
        )
    )
    serializer = CandidateApplicationListSerializer(applications, many=True)
    return Response(serializer.data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def withdraw_candidate_application(request, application_id):
    if request.user.account_type != Utilisateur.AccountType.CANDIDATE:
        return Response(
            {"detail": "Only candidate accounts can withdraw applications."},
            status=status.HTTP_403_FORBIDDEN,
        )

    with transaction.atomic():
        application = (
            Candidature.objects.select_for_update()
            .filter(pk=application_id, candidat=request.user)
            .first()
        )
        if application is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if application.statut == StatutSuiviCandidature.WITHDRAWN:
            return Response(
                {
                    "detail": "Application already withdrawn.",
                    "application_id": application.pk,
                    "status": application.statut,
                }
            )

        withdrawable_statuses = {
            StatutSuiviCandidature.SUBMITTED,
            StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
            StatutSuiviCandidature.SHORTLISTED,
        }
        if application.statut not in withdrawable_statuses:
            return Response(
                {"detail": "This application can no longer be withdrawn."},
                status=status.HTTP_409_CONFLICT,
            )

        application.statut = StatutSuiviCandidature.WITHDRAWN
        application.save(update_fields=["statut", "derniere_mise_a_jour"])

    return Response(
        {
            "detail": "Application withdrawn successfully.",
            "application_id": application.pk,
            "status": application.statut,
        }
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_candidate_external_application_status(request, application_id):
    if request.user.account_type != Utilisateur.AccountType.CANDIDATE:
        return Response(
            {"detail": "Only candidate accounts can update external application tracking."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = ExternalApplicationStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    target_status = serializer.validated_data["status"]

    with transaction.atomic():
        application = (
            Candidature.objects.select_for_update()
            .filter(pk=application_id, candidat=request.user)
            .first()
        )
        if application is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if application.statut in {
            StatutSuiviCandidature.SUBMITTED,
            StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
            StatutSuiviCandidature.REJECTED,
            StatutSuiviCandidature.WITHDRAWN,
        }:
            return Response(
                {"detail": "This application uses the internal BidWise workflow."},
                status=status.HTTP_409_CONFLICT,
            )

        if target_status == StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED:
            allowed_current_statuses = {
                StatutSuiviCandidature.VUE,
                StatutSuiviCandidature.INTERESSEE,
                StatutSuiviCandidature.POSTULEE_EXTERNEMENT,
                StatutSuiviCandidature.ABANDONNEE,
                StatutSuiviCandidature.EXTERNAL_CLICKED,
                StatutSuiviCandidature.EXTERNAL_REMIND_LATER,
                StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED,
            }
            if application.statut not in allowed_current_statuses:
                return Response(
                    {"detail": "This external application can no longer be confirmed."},
                    status=status.HTTP_409_CONFLICT,
                )

            if application.statut == StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED:
                return Response(
                    {
                        "detail": "External application already confirmed.",
                        "application_id": application.pk,
                        "status": application.statut,
                    }
                )

        if target_status == StatutSuiviCandidature.EXTERNAL_REMIND_LATER:
            allowed_current_statuses = {
                StatutSuiviCandidature.VUE,
                StatutSuiviCandidature.INTERESSEE,
                StatutSuiviCandidature.POSTULEE_EXTERNEMENT,
                StatutSuiviCandidature.ABANDONNEE,
                StatutSuiviCandidature.EXTERNAL_CLICKED,
                StatutSuiviCandidature.EXTERNAL_REMIND_LATER,
            }
            if application.statut not in allowed_current_statuses:
                detail = (
                    "External application already confirmed."
                    if application.statut == StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED
                    else "This external application can no longer be updated."
                )
                return Response(
                    {"detail": detail},
                    status=status.HTTP_409_CONFLICT,
                )

            if application.statut == StatutSuiviCandidature.EXTERNAL_REMIND_LATER:
                return Response(
                    {
                        "detail": "External application reminder already saved.",
                        "application_id": application.pk,
                        "status": application.statut,
                    }
                )

        application.statut = target_status
        if not application.submitted_at:
            application.submitted_at = timezone.now()
        if not application.contact_email:
            application.contact_email = request.user.email or ""
        application.save(
            update_fields=[
                "statut",
                "submitted_at",
                "contact_email",
                "derniere_mise_a_jour",
            ]
        )

    return Response(
        {
            "detail": "External application status updated successfully.",
            "application_id": application.pk,
            "status": application.statut,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_organization_opportunity_applications(request, opportunity_id):
    if request.user.account_type != Utilisateur.AccountType.ORGANIZATION:
        return Response(
            {"detail": "Only organization accounts can view received applications."},
            status=status.HTTP_403_FORBIDDEN,
        )

    opportunity = Opportunite.objects.filter(
        pk=opportunity_id,
        organisation=request.user,
    ).first()
    if opportunity is None:
        return Response(
            {"detail": "Opportunity not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    applications = (
        Candidature.objects.filter(opportunite=opportunity)
        .select_related("candidat", "candidat__profil", "cv")
        .order_by(
            F("submitted_at").desc(nulls_last=True),
            "-date_creation",
            "-id",
        )
    )
    serializer = OrganizationReceivedApplicationSerializer(
        applications,
        many=True,
        context={"request": request},
    )
    return Response(serializer.data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def reject_organization_opportunity_application(
    request,
    opportunity_id,
    application_id,
):
    if request.user.account_type != Utilisateur.AccountType.ORGANIZATION:
        return Response(
            {"detail": "Only organization accounts can reject applications."},
            status=status.HTTP_403_FORBIDDEN,
        )

    restore_serializer = OrganizationApplicationRestoreSerializer(data=request.data)
    restore_serializer.is_valid(raise_exception=True)
    restore_status = restore_serializer.validated_data.get("restore_status")

    with transaction.atomic():
        opportunity = Opportunite.objects.filter(
            pk=opportunity_id,
            organisation=request.user,
        ).first()
        if opportunity is None:
            return Response(
                {"detail": "Opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        application = (
            Candidature.objects.select_for_update()
            .filter(pk=application_id, opportunite=opportunity)
            .first()
        )
        if application is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if application.statut == StatutSuiviCandidature.REJECTED:
            if restore_status:
                application.statut = restore_status
                application.save(update_fields=["statut", "derniere_mise_a_jour"])
                return Response(
                    {
                        "detail": "Application restored successfully.",
                        "application_id": application.pk,
                        "status": application.statut,
                    }
                )

            return Response(
                {
                    "detail": "Application rejected successfully.",
                    "application_id": application.pk,
                    "status": application.statut,
                }
            )

        rejectable_statuses = {
            StatutSuiviCandidature.SUBMITTED,
            StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
            StatutSuiviCandidature.SHORTLISTED,
        }
        if application.statut not in rejectable_statuses:
            return Response(
                {"detail": "This application can no longer be rejected."},
                status=status.HTTP_409_CONFLICT,
            )

        application.statut = StatutSuiviCandidature.REJECTED
        application.save(update_fields=["statut", "derniere_mise_a_jour"])

    return Response(
        {
            "detail": "Application rejected successfully.",
            "application_id": application.pk,
            "status": application.statut,
        }
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def accept_organization_opportunity_application(
    request,
    opportunity_id,
    application_id,
):
    if request.user.account_type != Utilisateur.AccountType.ORGANIZATION:
        return Response(
            {"detail": "Only organization accounts can update applications."},
            status=status.HTTP_403_FORBIDDEN,
        )

    restore_serializer = OrganizationApplicationRestoreSerializer(data=request.data)
    restore_serializer.is_valid(raise_exception=True)
    restore_status = restore_serializer.validated_data.get("restore_status")

    with transaction.atomic():
        opportunity = Opportunite.objects.filter(
            pk=opportunity_id,
            organisation=request.user,
        ).first()
        if opportunity is None:
            return Response(
                {"detail": "Opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        application = (
            Candidature.objects.select_for_update()
            .filter(pk=application_id, opportunite=opportunity)
            .first()
        )
        if application is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if application.statut == StatutSuiviCandidature.SHORTLISTED:
            if restore_status:
                application.statut = restore_status
                application.save(update_fields=["statut", "derniere_mise_a_jour"])
                return Response(
                    {
                        "detail": "Application restored successfully.",
                        "application_id": application.pk,
                        "status": application.statut,
                    }
                )

            return Response(
                {
                    "detail": "Application shortlisted successfully.",
                    "application_id": application.pk,
                    "status": application.statut,
                }
            )

        acceptable_statuses = {
            StatutSuiviCandidature.SUBMITTED,
            StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
            StatutSuiviCandidature.REJECTED,
        }
        if application.statut not in acceptable_statuses:
            return Response(
                {"detail": "This application can no longer be shortlisted."},
                status=status.HTTP_409_CONFLICT,
            )

        application.statut = StatutSuiviCandidature.SHORTLISTED
        application.save(update_fields=["statut", "derniere_mise_a_jour"])

    return Response(
        {
            "detail": "Application shortlisted successfully.",
            "application_id": application.pk,
            "status": application.statut,
        }
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_organization_opportunity_application(
    request,
    opportunity_id,
    application_id,
):
    if request.user.account_type != Utilisateur.AccountType.ORGANIZATION:
        return Response(
            {"detail": "Only organization accounts can delete applications."},
            status=status.HTTP_403_FORBIDDEN,
        )

    with transaction.atomic():
        opportunity = Opportunite.objects.filter(
            pk=opportunity_id,
            organisation=request.user,
        ).first()
        if opportunity is None:
            return Response(
                {"detail": "Opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        application = (
            Candidature.objects.select_for_update()
            .filter(pk=application_id, opportunite=opportunity)
            .first()
        )
        if application is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted_application_id = application.pk
        application.delete()

    return Response(
        {
            "detail": "Application deleted successfully.",
            "application_id": deleted_application_id,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_organization_candidate_application_profile(request, application_id):
    if request.user.account_type != Utilisateur.AccountType.ORGANIZATION:
        return Response(
            {"detail": "Only organization accounts can view candidate application profiles."},
            status=status.HTTP_403_FORBIDDEN,
        )

    application = (
        Candidature.objects.filter(
            pk=application_id,
            opportunite__organisation=request.user,
        )
        .select_related("candidat", "candidat__profil", "opportunite", "cv")
        .first()
    )
    if application is None:
        return Response(
            {"detail": "Application not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if application.statut == StatutSuiviCandidature.SUBMITTED:
        application.statut = StatutSuiviCandidature.VIEWED_BY_ORGANIZATION
        application.save(update_fields=["statut", "derniere_mise_a_jour"])

    serializer = OrganizationCandidateApplicationProfileSerializer(
        application,
        context={"request": request},
    )
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_application_cover_letter(request):
    if request.user.account_type != Utilisateur.AccountType.CANDIDATE:
        return Response(
            {"detail": "Only candidate accounts can upload application documents."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = CoverLetterUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    uploaded_file = serializer.validated_data["file"]
    extension = Path(uploaded_file.name or "").suffix.lower()
    storage = ProfileResumeStorage()
    stored_name = storage.save(
        f"application_cover_letters/{request.user.pk}/{secrets.token_hex(16)}{extension}",
        uploaded_file,
    )
    url = storage.url(stored_name)
    if not url.startswith(("http://", "https://")):
        url = request.build_absolute_uri(url)

    return Response(
        {
            "url": url,
            "name": Path(uploaded_file.name or "cover-letter").name,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def apply_to_organization_opportunity(request, opportunity_id):
    if request.user.account_type != Utilisateur.AccountType.CANDIDATE:
        return Response(
            {"detail": "Only candidate accounts can submit applications."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = InternalApplicationCreateSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        opportunity = (
            Opportunite.objects.select_for_update()
            .select_related("source")
            .filter(pk=opportunity_id)
            .first()
        )
        if opportunity is None:
            return Response(
                {"detail": "Opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if opportunity.statut != StatutOpportunite.ACTIVE:
            return Response(
                {"detail": "Applications are closed for this opportunity."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            opportunity.source.nom != ORGANIZATION_SOURCE_NAME
            or opportunity.organisation_id is None
        ):
            return Response(
                {"detail": "This opportunity accepts applications on its external source."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if opportunity.type_opportunite not in INTERNAL_APPLICATION_TYPES:
            return Response(
                {"detail": "Direct applications are not available for calls for tender."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Candidature.objects.filter(
            candidat=request.user,
            opportunite=opportunity,
        ).exists():
            return Response(
                {"detail": "You have already applied to this opportunity."},
                status=status.HTTP_409_CONFLICT,
            )

        application = Candidature.objects.create(
            candidat=request.user,
            opportunite=opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            cv=serializer.context["resume"],
            cover_letter_url=serializer.validated_data.get("cover_letter_url", ""),
            contact_email=serializer.validated_data["contact_email"],
            contact_phone=serializer.validated_data.get("contact_phone", ""),
            submitted_at=timezone.now(),
        )
        
        # Dispatch notification email tasks after the transaction commits.
        transaction.on_commit(
            lambda: notify_organization_new_application_task.delay(application_id=application.pk)
        )
        transaction.on_commit(
            lambda: notify_candidate_application_submitted_task.delay(application_id=application.pk)
        )

    return Response(
        {
            "detail": "Application submitted successfully.",
            "application_id": application.pk,
            "status": application.statut,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_external_application_click(request, opportunity_id):
    if request.user.account_type != Utilisateur.AccountType.CANDIDATE:
        return Response(
            {"detail": "Only candidate accounts can track external applications."},
            status=status.HTTP_403_FORBIDDEN,
        )

    with transaction.atomic():
        opportunity = (
            Opportunite.objects.select_for_update()
            .select_related("source")
            .filter(pk=opportunity_id)
            .first()
        )
        if opportunity is None:
            return Response(
                {"detail": "Opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if opportunity.statut != StatutOpportunite.ACTIVE:
            return Response(
                {"detail": "Applications are closed for this opportunity."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            opportunity.source.nom == ORGANIZATION_SOURCE_NAME
            and opportunity.organisation_id is not None
        ):
            return Response(
                {"detail": "Use the direct BidWise application flow for this opportunity."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        external_url = str(opportunity.source_item_url or "").strip()
        if not external_url:
            return Response(
                {"detail": "This opportunity does not provide an external application link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application = (
            Candidature.objects.select_for_update()
            .filter(candidat=request.user, opportunite=opportunity)
            .first()
        )
        if application is None:
            application = Candidature.objects.create(
                candidat=request.user,
                opportunite=opportunity,
                statut=StatutSuiviCandidature.EXTERNAL_CLICKED,
                url_source=external_url,
                contact_email=request.user.email or "",
                submitted_at=timezone.now(),
            )
            return Response(
                {
                    "detail": "External application tracking started.",
                    "application_id": application.pk,
                    "status": application.statut,
                },
                status=status.HTTP_201_CREATED,
            )

        if application.statut in {
            StatutSuiviCandidature.SUBMITTED,
            StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
            StatutSuiviCandidature.REJECTED,
            StatutSuiviCandidature.WITHDRAWN,
        }:
            return Response(
                {"detail": "You already have an internal application for this opportunity."},
                status=status.HTTP_409_CONFLICT,
            )

        if application.statut == StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED:
            if application.url_source != external_url:
                application.url_source = external_url
                application.save(update_fields=["url_source", "derniere_mise_a_jour"])
            return Response(
                {
                    "detail": "External application already confirmed.",
                    "application_id": application.pk,
                    "status": application.statut,
                }
            )

        application.statut = StatutSuiviCandidature.EXTERNAL_CLICKED
        application.url_source = external_url
        if not application.submitted_at:
            application.submitted_at = timezone.now()
        if not application.contact_email:
            application.contact_email = request.user.email or ""
        application.save(
            update_fields=[
                "statut",
                "url_source",
                "submitted_at",
                "contact_email",
                "derniere_mise_a_jour",
            ]
        )

    return Response(
        {
            "detail": "External application tracking updated.",
            "application_id": application.pk,
            "status": application.statut,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_organization_applications(request):
    """List all applications for all opportunities belonging to the authenticated organization."""
    if request.user.account_type != Utilisateur.AccountType.ORGANIZATION:
        return Response(
            {"detail": "Only organization accounts can view applications."},
            status=status.HTTP_403_FORBIDDEN,
        )

    applications = (
        Candidature.objects.filter(opportunite__organisation=request.user)
        .select_related("candidat", "candidat__profil", "opportunite")
        .order_by(F("submitted_at").desc(nulls_last=True))
    )
    serializer = OrganizationAllApplicationsSerializer(
        applications, 
        many=True,
        context={"request": request}
    )
    return Response(serializer.data)


class CandidatureViewSet(viewsets.ModelViewSet):
    serializer_class = CandidatureSerializer
    permission_classes = [IsAuthenticated, IsOwnerCandidature]

    def get_queryset(self):
        return Candidature.objects.filter(
            candidat=self.request.user,
        ).order_by("-date_creation", "-id")

    def perform_create(self, serializer):
        serializer.save(candidat=self.request.user)
