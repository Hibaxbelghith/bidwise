from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    OpportuniteViewSet,
    SourceOpportuniteViewSet,
    pipeline_metrics_view,
)

router = DefaultRouter()
router.register(r'opportunities', OpportuniteViewSet, basename='opportunity')
router.register(r'opportunites', OpportuniteViewSet, basename='opportunite-legacy')
router.register(r'sources', SourceOpportuniteViewSet, basename='source')


urlpatterns = [
	path('metrics/pipeline/', pipeline_metrics_view, name='pipeline_metrics'),
]
urlpatterns += router.urls
