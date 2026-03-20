from rest_framework.routers import DefaultRouter
from .views import OpportuniteViewSet, SourceOpportuniteViewSet

router = DefaultRouter()
router.register(r'opportunities', OpportuniteViewSet, basename='opportunity')
router.register(r'opportunites', OpportuniteViewSet, basename='opportunite-legacy')
router.register(r'sources', SourceOpportuniteViewSet, basename='source')


urlpatterns = router.urls
