from django.urls import path
from rest_framework.routers import DefaultRouter
from applications.views import (
	accept_organization_opportunity_application,
	delete_organization_opportunity_application,
	get_organization_candidate_application_profile,
	list_organization_opportunity_applications,
	reject_organization_opportunity_application,
	list_organization_applications,
)

from .views import (
    OpportuniteViewSet,
    SourceOpportuniteViewSet,
    organization_description_draft_view,
    organization_opportunities_view,
    organization_opportunity_detail_view,
    organization_opportunity_status_action_view,
    organization_tender_document_upload_view,
    pipeline_metrics_view,
    tender_recommendations_view,
)
from .views_admin import (
    AdminDashboardView,
    AdminLoginView,
    AdminAuditLogViewSet,
    AdminOpportunityViewSet,
    AdminOrganizationOpportunityDecisionView,
    AdminPendingOrganizationOpportunitiesView,
    AdminSchedulerStateView,
    AdminTestView,
    AdminUserViewSet,
)

router = DefaultRouter()
router.register(r'opportunities', OpportuniteViewSet, basename='opportunity')
router.register(r'opportunites', OpportuniteViewSet, basename='opportunite-legacy')
router.register(r'sources', SourceOpportuniteViewSet, basename='source')
router.register(r'admin/opportunities', AdminOpportunityViewSet, basename='admin-opportunity')
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')
router.register(r'admin/audit-logs', AdminAuditLogViewSet, basename='admin-audit-log')


urlpatterns = [
    # Admin
    path('admin/login/', AdminLoginView.as_view(), name='admin_login'),
    path('admin/test/', AdminTestView.as_view(), name='admin_test'),
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/organization-opportunities/pending/', AdminPendingOrganizationOpportunitiesView.as_view(), name='admin_organization_opportunities_pending'),
    path('admin/organization-opportunities/<int:pk>/approve/', AdminOrganizationOpportunityDecisionView.as_view(), {"decision": "approve"}, name='admin_organization_opportunity_approve'),
    path('admin/organization-opportunities/<int:pk>/reject/', AdminOrganizationOpportunityDecisionView.as_view(), {"decision": "reject"}, name='admin_organization_opportunity_reject'),
    path('admin/scheduler-state/', AdminSchedulerStateView.as_view(), name='admin_scheduler_state'),
    path('metrics/pipeline/', pipeline_metrics_view, name='pipeline_metrics'),
    path('opportunities/tenders/recommendations/', tender_recommendations_view, name='tender_recommendations'),

    # Organization
    path('organization/opportunities/', organization_opportunities_view, name='organization_opportunities'),
    path('organization/opportunities/description-draft/', organization_description_draft_view, name='organization_description_draft'),
    path('organization/opportunities/tender-documents/', organization_tender_document_upload_view, name='organization_tender_document_upload'),
    path('organization/applications/', list_organization_applications, name='list_organization_applications'),
    path(
        'organization/applications/<int:application_id>/candidate-profile/',
        get_organization_candidate_application_profile,
        name='organization_candidate_application_profile',
    ),

  
    path(
        'organization/opportunities/<int:opportunity_id>/applications/',
        list_organization_opportunity_applications,
        name='list_organization_opportunity_applications',
    ),
	path(
		'organization/opportunities/<int:opportunity_id>/applications/<int:application_id>/reject/',
		reject_organization_opportunity_application,
		name='reject_organization_opportunity_application',
	),
	path(
		'organization/opportunities/<int:opportunity_id>/applications/<int:application_id>/accept/',
		accept_organization_opportunity_application,
		name='accept_organization_opportunity_application',
	),
	path(
		'organization/opportunities/<int:opportunity_id>/applications/<int:application_id>/',
		delete_organization_opportunity_application,
		name='delete_organization_opportunity_application',
	),

   
    path('organization/opportunities/<int:pk>/', organization_opportunity_detail_view, name='organization_opportunity_detail'),
    path('organization/opportunities/<int:pk>/<str:action>/', organization_opportunity_status_action_view, name='organization_opportunity_status_action'),
]
urlpatterns += router.urls
