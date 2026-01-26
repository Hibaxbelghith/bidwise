from rest_framework.routers import DefaultRouter
from .views import OpportuniteViewSet, SourceOpportuniteViewSet

router = DefaultRouter()
router.register(r'opportunites', OpportuniteViewSet, basename='opportunite')
router.register(r'sources', SourceOpportuniteViewSet, basename='source')


urlpatterns = router.urls
