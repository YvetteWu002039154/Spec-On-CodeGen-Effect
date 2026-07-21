from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.urls import include, path
from django.utils import timezone

from rest_framework import permissions, routers, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters import rest_framework as filters

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


# =========================
# Models
# =========================

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    inventory = models.PositiveIntegerField(default=0)
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["title", "author"]

    def clean(self) -> None:
        if self.daily_fee < 0:
            raise ValidationError({"daily_fee": "Daily fee must be non-negative."})

    def __str__(self) -> str:
        return f"{self.title} by {self.author}"


class Borrowing(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="borrowings")
    borrow_date = models.DateField(default=date.today)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-borrow_date", "-id"]

    def clean(self) -> None:
        if self.expected_return_date is None:
            raise ValidationError({"expected_return_date": "Expected return date is required."})
        if self.expected_return_date < self.borrow_date:
            raise ValidationError({"expected_return_date": "Expected return date cannot be before borrow date."})
        if self.actual_return_date is not None and self.actual_return_date < self.borrow_date:
            raise ValidationError({"actual_return_date": "Actual return date cannot be before borrow date."})

    @property
    def is_returned(self) -> bool:
        return self.actual_return_date is not None

    def __str__(self) -> str:
        return f"Borrowing #{self.pk} - {self.user} - {self.book}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    class Type(models.TextChoices):
        BORROWING = "BORROWING", "Borrowing"
        FINE = "FINE", "Fine"

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name="payments")
    payment_type = models.CharField(max_length=16, choices=Type.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def clean(self) -> None:
        if self.amount < 0:
            raise ValidationError({"amount": "Amount must be non-negative."})

    def mark_paid(self) -> None:
        if self.status == self.Status.PAID:
            return
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])

    def __str__(self) -> str:
        return f"Payment #{self.pk} ({self.payment_type}) - {self.status} - {self.amount}"


# =========================
# Business logic helpers
# =========================

def _days_between(start: date, end: date) -> int:
    delta = (end - start).days
    return max(0, int(delta))


def calculate_borrowing_amount(borrowing: Borrowing) -> Decimal:
    days = _days_between(borrowing.borrow_date, borrowing.expected_return_date)
    return (Decimal(days) * borrowing.book.daily_fee).quantize(Decimal("0.01"))


def calculate_fine_amount(borrowing: Borrowing, actual_return_date: date) -> Decimal:
    overdue_days = _days_between(borrowing.expected_return_date, actual_return_date)
    if overdue_days <= 0:
        return Decimal("0.00")
    fine_multiplier = Decimal("2.00")
    return (Decimal(overdue_days) * borrowing.book.daily_fee * fine_multiplier).quantize(Decimal("0.01"))


# =========================
# Serializers
# =========================

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title", "author", "inventory", "daily_fee"]


class BorrowingSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())

    class Meta:
        model = Borrowing
        fields = [
            "id",
            "user",
            "book",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
        ]
        read_only_fields = ["borrow_date", "actual_return_date"]

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        expected = attrs.get("expected_return_date")
        if expected is None:
            raise serializers.ValidationError({"expected_return_date": "Expected return date is required."})
        borrow_date = date.today()
        if expected < borrow_date:
            raise serializers.ValidationError({"expected_return_date": "Expected return date cannot be before borrow date."})
        book: Book = attrs.get("book")
        if book is None:
            raise serializers.ValidationError({"book": "Book is required."})
        if book.inventory <= 0:
            raise serializers.ValidationError({"book": "Book is out of stock."})
        return attrs

    def create(self, validated_data: Dict[str, Any]) -> Borrowing:
        request: Request = self.context["request"]
        user = request.user
        book: Book = validated_data["book"]
        expected = validated_data["expected_return_date"]

        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=book.pk)
            if book.inventory <= 0:
                raise serializers.ValidationError({"book": "Book is out of stock."})
            book.inventory -= 1
            book.save(update_fields=["inventory"])

            borrowing = Borrowing.objects.create(
                user=user,
                book=book,
                borrow_date=date.today(),
                expected_return_date=expected,
            )

            amount = calculate_borrowing_amount(borrowing)
            Payment.objects.create(
                borrowing=borrowing,
                payment_type=Payment.Type.BORROWING,
                status=Payment.Status.PENDING,
                amount=amount,
            )
        return borrowing


class BorrowingReturnSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField(required=False)

    def validate_actual_return_date(self, value: date) -> date:
        if value > date.today():
            raise serializers.ValidationError("Actual return date cannot be in the future.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "borrowing", "payment_type", "status", "amount", "created_at", "paid_at"]
        read_only_fields = ["created_at", "paid_at"]


class PaymentPaySerializer(serializers.Serializer):
    paid = serializers.BooleanField(default=True)

    def validate_paid(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError("Only paying (paid=true) is supported.")
        return value


# =========================
# Filters
# =========================

class BorrowingFilter(filters.FilterSet):
    actual_return_date = filters.DateFilter(field_name="actual_return_date")
    user = filters.NumberFilter(field_name="user_id")

    class Meta:
        model = Borrowing
        fields = ["actual_return_date", "user"]


class PaymentFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    payment_type = filters.CharFilter(field_name="payment_type")
    borrowing = filters.NumberFilter(field_name="borrowing_id")

    class Meta:
        model = Payment
        fields = ["status", "payment_type", "borrowing"]


class BookFilter(filters.FilterSet):
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    author = filters.CharFilter(field_name="author", lookup_expr="icontains")

    class Meta:
        model = Book
        fields = ["title", "author"]


# =========================
# Permissions
# =========================

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request: Request, view: viewsets.ViewSet) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request: Request, view: viewsets.ViewSet, obj: Any) -> bool:
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        if hasattr(obj, "user_id"):
            return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.id)
        if hasattr(obj, "borrowing") and hasattr(obj.borrowing, "user_id"):
            return bool(request.user and request.user.is_authenticated and obj.borrowing.user_id == request.user.id)
        return False


# =========================
# ViewSets
# =========================

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


# =========================
# Admin
# =========================

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "inventory", "daily_fee")
    search_fields = ("title", "author")
    list_filter = ("author",)
    ordering = ("title",)


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "book", "borrow_date", "expected_return_date", "actual_return_date")
    list_filter = ("actual_return_date", "borrow_date")
    search_fields = ("user__username", "user__email", "book__title", "book__author")
    ordering = ("-borrow_date", "-id")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "borrowing", "payment_type", "status", "amount", "created_at", "paid_at")
    list_filter = ("status", "payment_type", "created_at")
    search_fields = ("borrowing__user__username", "borrowing__book__title", "borrowing__book__author")
    ordering = ("-created_at", "-id")


# =========================
# URLs / Router
# =========================

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