# =========================
# URLs / Router
# =========================
from rest_framework import permissions, routers, serializers, status, viewsets
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.views import BookViewSet, BorrowingViewSet, PaymentViewSet

from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

router = routers.DefaultRouter()
router.register(r"books", BookViewSet, basename="books")
router.register(r"borrowings", BorrowingViewSet, basename="borrowings")
router.register(r"payments", PaymentViewSet, basename="payments")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/doc/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/doc/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/", include(router.urls)),
]