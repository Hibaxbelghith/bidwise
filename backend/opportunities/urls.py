from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    OpportuniteViewSet,
    SourceOpportuniteViewSet,
    pipeline_metrics_view,
)
from .views_admin import (
    AdminDashboardView,
    AdminLoginView,
    AdminOpportunityViewSet,
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


urlpatterns = [
	path('admin/login/', AdminLoginView.as_view(), name='admin_login'),
	path('admin/test/', AdminTestView.as_view(), name='admin_test'),
	path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
	path('admin/scheduler-state/', AdminSchedulerStateView.as_view(), name='admin_scheduler_state'),
	path('metrics/pipeline/', pipeline_metrics_view, name='pipeline_metrics'),
]
urlpatterns += router.urls
