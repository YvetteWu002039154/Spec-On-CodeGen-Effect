# =========================
# ViewSets
# =========================
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework import permissions, routers, serializers, status, viewsets
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters import rest_framework as filters

from api.models import Book, Borrowing, Payment
from api.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from api.serializers import BookSerializer, BorrowingReturnSerializer, BorrowingSerializer, PaymentPaySerializer, PaymentSerializer
from api.filters import BookFilter, BorrowingFilter, PaymentFilter

from typing import Any, Dict, List, Optional, Tuple

@extend_schema_view(
    list=extend_schema(tags=["Books"]),
    retrieve=extend_schema(tags=["Books"]),
    create=extend_schema(tags=["Books"]),
    update=extend_schema(tags=["Books"]),
    partial_update=extend_schema(tags=["Books"]),
    destroy=extend_schema(tags=["Books"]),
)
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BookFilter
    search_fields = ["title", "author"]
    ordering_fields = ["title", "author", "inventory", "daily_fee"]
    ordering = ["title"]


@extend_schema_view(
    list=extend_schema(tags=["Borrowings"]),
    retrieve=extend_schema(tags=["Borrowings"]),
    create=extend_schema(tags=["Borrowings"]),
)
class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.select_related("user", "book").all()
    serializer_class = BorrowingSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    http_method_names = ["get", "post", "head", "options"]
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    filterset_class = BorrowingFilter
    ordering_fields = ["borrow_date", "expected_return_date", "actual_return_date", "id"]
    ordering = ["-borrow_date", "-id"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer: BorrowingSerializer) -> None:
        serializer.save()

    @extend_schema(tags=["Borrowings"], request=BorrowingReturnSerializer, responses={200: BorrowingSerializer})
    @action(detail=True, methods=["post"], url_path="return", permission_classes=[permissions.IsAuthenticated, IsOwnerOrAdmin])
    def return_book(self, request: Request, pk: Optional[str] = None) -> Response:
        borrowing = self.get_object()
        ser = BorrowingReturnSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        if borrowing.actual_return_date is not None:
            return Response({"detail": "Borrowing is already returned."}, status=status.HTTP_400_BAD_REQUEST)

        actual_return_date = ser.validated_data.get("actual_return_date") or date.today()

        with transaction.atomic():
            borrowing = Borrowing.objects.select_for_update().select_related("book").get(pk=borrowing.pk)
            if borrowing.actual_return_date is not None:
                return Response({"detail": "Borrowing is already returned."}, status=status.HTTP_400_BAD_REQUEST)

            borrowing.actual_return_date = actual_return_date
            borrowing.full_clean()
            borrowing.save(update_fields=["actual_return_date"])

            book = borrowing.book
            book.inventory = models.F("inventory") + 1
            book.save(update_fields=["inventory"])

            fine_amount = calculate_fine_amount(borrowing, actual_return_date)
            if fine_amount > 0:
                Payment.objects.create(
                    borrowing=borrowing,
                    payment_type=Payment.Type.FINE,
                    status=Payment.Status.PENDING,
                    amount=fine_amount,
                )

        borrowing.refresh_from_db()
        return Response(BorrowingSerializer(borrowing, context={"request": request}).data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(tags=["Payments"]),
    retrieve=extend_schema(tags=["Payments"]),
)
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.select_related("borrowing", "borrowing__user", "borrowing__book").all()
    serializer_class = PaymentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ["created_at", "amount", "status", "payment_type", "id"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(borrowing__user=user)

    @extend_schema(tags=["Payments"], request=PaymentPaySerializer, responses={200: PaymentSerializer})
    @action(detail=True, methods=["post"], url_path="pay", permission_classes=[permissions.IsAuthenticated, IsOwnerOrAdmin])
    def pay(self, request: Request, pk: Optional[str] = None) -> Response:
        payment = self.get_object()
        ser = PaymentPaySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        if payment.status == Payment.Status.PAID:
            return Response(PaymentSerializer(payment, context={"request": request}).data, status=status.HTTP_200_OK)

        payment.mark_paid()
        payment.refresh_from_db()
        return Response(PaymentSerializer(payment, context={"request": request}).data, status=status.HTTP_200_OK)

