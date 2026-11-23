from rest_framework.routers import DefaultRouter

from scheduling.views import AvailabilityViewSet, DoctorViewSet

router = DefaultRouter()
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("availability", AvailabilityViewSet, basename="availability")

urlpatterns = router.urls
