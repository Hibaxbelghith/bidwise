from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    OpportuniteViewSet,
    SourceOpportuniteViewSet,
    organization_opportunities_view,
    organization_tender_document_upload_view,
    pipeline_metrics_view,
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
	path('admin/login/', AdminLoginView.as_view(), name='admin_login'),
	path('admin/test/', AdminTestView.as_view(), name='admin_test'),
	path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
	path('admin/organization-opportunities/pending/', AdminPendingOrganizationOpportunitiesView.as_view(), name='admin_organization_opportunities_pending'),
	path('admin/organization-opportunities/<int:pk>/approve/', AdminOrganizationOpportunityDecisionView.as_view(), {"decision": "approve"}, name='admin_organization_opportunity_approve'),
	path('admin/organization-opportunities/<int:pk>/reject/', AdminOrganizationOpportunityDecisionView.as_view(), {"decision": "reject"}, name='admin_organization_opportunity_reject'),
	path('admin/scheduler-state/', AdminSchedulerStateView.as_view(), name='admin_scheduler_state'),
	path('metrics/pipeline/', pipeline_metrics_view, name='pipeline_metrics'),
	path('organization/opportunities/', organization_opportunities_view, name='organization_opportunities'),
	path('organization/opportunities/tender-documents/', organization_tender_document_upload_view, name='organization_tender_document_upload'),
]
urlpatterns += router.urls
