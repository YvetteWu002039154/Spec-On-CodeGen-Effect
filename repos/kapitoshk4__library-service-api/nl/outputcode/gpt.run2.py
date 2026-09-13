from __future__ import annotations

from datetime import date, timedelta
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
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from django_filters import rest_framework as filters

from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


# -----------------------------
# Models
# -----------------------------

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    inventory = models.PositiveIntegerField(default=0)
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["title", "author"]

    def __str__(self) -> str:
        return f"{self.title} by {self.author}"

    def clean(self) -> None:
        if self.daily_fee < 0:
            raise ValidationError({"daily_fee": "Daily fee must be non-negative."})

    def available_count(self) -> int:
        active = Borrowing.objects.filter(book=self, actual_return_date__isnull=True).count()
        available = int(self.inventory) - int(active)
        return max(0, available)


class Borrowing(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="borrowings")
    borrow_date = models.DateField(default=date.today)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-borrow_date", "-id"]

    def __str__(self) -> str:
        return f"Borrowing({self.user_id}, {self.book_id}, {self.borrow_date})"

    def clean(self) -> None:
        if self.expected_return_date and self.borrow_date and self.expected_return_date < self.borrow_date:
            raise ValidationError({"expected_return_date": "Expected return date cannot be before borrow date."})
        if self.actual_return_date and self.actual_return_date < self.borrow_date:
            raise ValidationError({"actual_return_date": "Actual return date cannot be before borrow date."})

    @property
    def is_active(self) -> bool:
        return self.actual_return_date is None

    def is_overdue(self, on_date: Optional[date] = None) -> bool:
        if on_date is None:
            on_date = date.today()
        if self.actual_return_date is not None:
            return self.actual_return_date > self.expected_return_date
        return on_date > self.expected_return_date

    def days_borrowed(self, until: Optional[date] = None) -> int:
        if until is None:
            until = self.actual_return_date or date.today()
        delta = (until - self.borrow_date).days
        return max(0, delta)

    def overdue_days(self) -> int:
        end = self.actual_return_date or date.today()
        if end <= self.expected_return_date:
            return 0
        return (end - self.expected_return_date).days

    def base_amount(self) -> Decimal:
        days = self.days_borrowed(self.actual_return_date or date.today())
        return (Decimal(days) * self.book.daily_fee).quantize(Decimal("0.01"))

    def fine_amount(self) -> Decimal:
        overdue = self.overdue_days()
        if overdue <= 0:
            return Decimal("0.00")
        fine_rate = getattr(settings, "LIBRARY_FINE_MULTIPLIER", Decimal("2.00"))
        if not isinstance(fine_rate, Decimal):
            fine_rate = Decimal(str(fine_rate))
        amount = (Decimal(overdue) * self.book.daily_fee * fine_rate).quantize(Decimal("0.01"))
        return amount

    def total_amount(self) -> Decimal:
        return (self.base_amount() + self.fine_amount()).quantize(Decimal("0.01"))

    def can_be_borrowed(self) -> bool:
        return self.book.available_count() > 0


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Payment({self.borrowing_id}, {self.amount}, {self.status})"

    def clean(self) -> None:
        if self.amount < 0:
            raise ValidationError({"amount": "Amount must be non-negative."})

    def mark_paid(self) -> None:
        if self.status == self.Status.PAID:
            return
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])


# -----------------------------
# Admin
# -----------------------------

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "inventory", "daily_fee")
    search_fields = ("title", "author")
    list_filter = ("author",)


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "book", "borrow_date", "expected_return_date", "actual_return_date")
    search_fields = ("user__username", "user__email", "book__title", "book__author")
    list_filter = ("actual_return_date", "borrow_date", "expected_return_date")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "borrowing", "amount", "status", "created_at", "paid_at")
    list_filter = ("status", "created_at")
    search_fields = ("borrowing__user__username", "borrowing__book__title")


# -----------------------------
# Permissions
# -----------------------------

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request: Request, view: viewsets.ViewSet) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request: Request, view: viewsets.ViewSet, obj: Any) -> bool:
        if bool(request.user and request.user.is_authenticated and request.user.is_staff):
            return True
        if hasattr(obj, "user_id"):
            return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.id)
        if hasattr(obj, "borrowing") and hasattr(obj.borrowing, "user_id"):
            return bool(request.user and request.user.is_authenticated and obj.borrowing.user_id == request.user.id)
        return False


# -----------------------------
# Serializers
# -----------------------------

class BookSerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ("id", "title", "author", "inventory", "daily_fee", "available")

    def get_available(self, obj: Book) -> int:
        return obj.available_count()


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id", "book", "borrow_date", "expected_return_date")
        read_only_fields = ("id",)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        borrow_date = attrs.get("borrow_date") or date.today()
        expected = attrs.get("expected_return_date")
        if expected is None:
            raise serializers.ValidationError({"expected_return_date": "This field is required."})
        if expected < borrow_date:
            raise serializers.ValidationError({"expected_return_date": "Expected return date cannot be before borrow date."})
        book: Book = attrs["book"]
        if book.available_count() <= 0:
            raise serializers.ValidationError({"book": "Book is not available."})
        return attrs

    def create(self, validated_data: Dict[str, Any]) -> Borrowing:
        request = self.context["request"]
        user = request.user
        borrowing = Borrowing(user=user, **validated_data)
        borrowing.full_clean()
        borrowing.save()
        return borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(source="book", queryset=Book.objects.all(), write_only=True, required=False)
    base_amount = serializers.SerializerMethodField()
    fine_amount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "user",
            "book",
            "book_id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "is_overdue",
            "base_amount",
            "fine_amount",
            "total_amount",
        )
        read_only_fields = ("id", "user", "book", "is_overdue", "base_amount", "fine_amount", "total_amount")

    def get_base_amount(self, obj: Borrowing) -> str:
        return str(obj.base_amount())

    def get_fine_amount(self, obj: Borrowing) -> str:
        return str(obj.fine_amount())

    def get_total_amount(self, obj: Borrowing) -> str:
        return str(obj.total_amount())

    def get_is_overdue(self, obj: Borrowing) -> bool:
        return obj.is_overdue()


class BorrowingReturnSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField(required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        borrowing: Borrowing = self.context["borrowing"]
        if borrowing.actual_return_date is not None:
            raise serializers.ValidationError("Borrowing is already returned.")
        actual = attrs.get("actual_return_date") or date.today()
        if actual < borrowing.borrow_date:
            raise serializers.ValidationError({"actual_return_date": "Actual return date cannot be before borrow date."})
        attrs["actual_return_date"] = actual
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    borrowing_id = serializers.PrimaryKeyRelatedField(source="borrowing", queryset=Borrowing.objects.all(), write_only=True)
    borrowing = BorrowingSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ("id", "borrowing", "borrowing_id", "amount", "status", "created_at", "paid_at")
        read_only_fields = ("id", "status", "created_at", "paid_at", "borrowing")

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        borrowing: Borrowing = attrs["borrowing"]
        request = self.context["request"]
        if not (request.user.is_staff or borrowing.user_id == request.user.id):
            raise serializers.ValidationError("Not allowed.")
        if borrowing.actual_return_date is None:
            raise serializers.ValidationError({"borrowing_id": "Borrowing must be returned before payment."})
        amount = borrowing.total_amount()
        attrs["amount"] = amount
        return attrs

    def create(self, validated_data: Dict[str, Any]) -> Payment:
        borrowing: Borrowing = validated_data["borrowing"]
        amount: Decimal = validated_data["amount"]
        payment = Payment(borrowing=borrowing, amount=amount, status=Payment.Status.PENDING)
        payment.full_clean()
        payment.save()
        return payment


class PaymentMarkPaidSerializer(serializers.Serializer):
    pass


# -----------------------------
# Filters
# -----------------------------

class BorrowingFilter(filters.FilterSet):
    actual_return_date = filters.DateFilter(field_name="actual_return_date")
    actual_return_date__isnull = filters.BooleanFilter(field_name="actual_return_date", lookup_expr="isnull")
    user = filters.NumberFilter(field_name="user_id")

    class Meta:
        model = Borrowing
        fields = ("actual_return_date", "actual_return_date__isnull", "user")


class BookFilter(filters.FilterSet):
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    author = filters.CharFilter(field_name="author", lookup_expr="icontains")

    class Meta:
        model = Book
        fields = ("title", "author")


class PaymentFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    borrowing = filters.NumberFilter(field_name="borrowing_id")
    user = filters.NumberFilter(method="filter_user")

    def filter_user(self, queryset: models.QuerySet, name: str, value: Any) -> models.QuerySet:
        return queryset.filter(borrowing__user_id=value)

    class Meta:
        model = Payment
        fields = ("status", "borrowing", "user")


# -----------------------------
# Pagination
# -----------------------------

class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# -----------------------------
# ViewSets
# -----------------------------

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
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = DefaultPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = BookFilter
    search_fields = ("title", "author")
    ordering_fields = ("title", "author", "inventory", "daily_fee")
    ordering = ("title",)


@extend_schema_view(
    list=extend_schema(tags=["Borrowings"]),
    retrieve=extend_schema(tags=["Borrowings"]),
    create=extend_schema(tags=["Borrowings"]),
    update=extend_schema(tags=["Borrowings"]),
    partial_update=extend_schema(tags=["Borrowings"]),
    destroy=extend_schema(tags=["Borrowings"]),
)
class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.select_related("user", "book").all()
    serializer_class = BorrowingSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwnerOrAdmin)
    pagination_class = DefaultPagination
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = BorrowingFilter
    search_fields = ("book__title", "book__author", "user__username", "user__email")
    ordering_fields = ("borrow_date", "expected_return_date", "actual_return_date", "id")
    ordering = ("-borrow_date",)

    def get_queryset(self) -> models.QuerySet:
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(user=user)

    def get_serializer_class(self) -> type[serializers.Serializer]:
        if self.action == "create":
            return BorrowingCreateSerializer
        if self.action == "return_book":
            return BorrowingReturnSerializer
        return BorrowingSerializer

    def perform_create(self, serializer: serializers.Serializer) -> None:
        serializer.save()

    @extend_schema(tags=["Borrowings"], request=BorrowingReturnSerializer, responses=BorrowingSerializer)
    @action(methods=["post"], detail=True, url_path="return", permission_classes=(permissions.IsAuthenticated, IsOwnerOrAdmin))
    def return_book(self, request: Request, pk: Optional[str] = None) -> Response:
        borrowing = self.get_object()
        serializer = self.get_serializer(data=request.data, context={"request": request, "borrowing": borrowing})
        serializer.is_valid(raise_exception=True)
        actual_return_date: date = serializer.validated_data["actual_return_date"]
        borrowing.actual_return_date = actual_return_date
        borrowing.full_clean()
        borrowing.save(update_fields=["actual_return_date"])
        out = BorrowingSerializer(borrowing, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(tags=["Payments"]),
    retrieve=extend_schema(tags=["Payments"]),
    create=extend_schema(tags=["Payments"]),
    destroy=extend_schema(tags=["Payments"]),
)
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("borrowing", "borrowing__user", "borrowing__book").all()
    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwnerOrAdmin)
    pagination_class = DefaultPagination
    http_method_names = ["get", "post", "delete"]
    filter_backends = (filters.DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = PaymentFilter
    search_fields = ("borrowing__book__title", "borrowing__book__author", "borrowing__user__username", "borrowing__user__email")
    ordering_fields = ("created_at", "paid_at", "amount", "status", "id")
    ordering = ("-created_at",)

    def get_queryset(self) -> models.QuerySet:
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(borrowing__user=user)

    @extend_schema(tags=["Payments"], request=PaymentMarkPaidSerializer, responses=PaymentSerializer)
    @action(methods=["post"], detail=True, url_path="pay", permission_classes=(permissions.IsAuthenticated, IsOwnerOrAdmin))
    def pay(self, request: Request, pk: Optional[str] = None) -> Response:
        payment = self.get_object()
        if payment.status == Payment.Status.PAID:
            serializer = PaymentSerializer(payment, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        with transaction.atomic():
            payment.mark_paid()
        serializer = PaymentSerializer(payment, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------------
# Router & URLs
# -----------------------------

router = routers.DefaultRouter()
router.register(r"books", BookViewSet, basename="book")
router.register(r"borrowings", BorrowingViewSet, basename="borrowing")
router.register(r"payments", PaymentViewSet, basename="payment")

api_v1_urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("doc/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("doc/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("", include(router.urls)),
]

urlpatterns = [
    path("api/v1/", include((api_v1_urlpatterns, "api"), namespace="v1")),
]