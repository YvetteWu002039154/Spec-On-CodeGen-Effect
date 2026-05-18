import os
import sys
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional

import django
from django.conf import settings
from django.core.management import execute_from_command_line
from django.db import models, transaction
from django.contrib.auth.models import User
from django.urls import path, include
from django.contrib import admin

from rest_framework import serializers, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
import django_filters
from django_filters.rest_framework import DjangoFilterBackend

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='library-service-secret-key',
        ROOT_URLCONF=__name__,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'rest_framework',
            'rest_framework_simplejwt',
            'django_filters',
            'drf_spectacular',
            '__main__',
        ],
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ],
        REST_FRAMEWORK={
            'DEFAULT_AUTHENTICATION_CLASSES': (
                'rest_framework_simplejwt.authentication.JWTAuthentication',
            ),
            'DEFAULT_PERMISSION_CLASSES': (
                'rest_framework.permissions.IsAuthenticated',
            ),
            'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
            'DEFAULT_FILTER_BACKENDS': [
                'django_filters.rest_framework.DjangoFilterBackend'
            ],
        },
        SPECTACULAR_SETTINGS={
            'TITLE': 'Library Service API',
            'DESCRIPTION': 'API Library service for borrowing books',
            'VERSION': '1.0.0',
            'SERVE_INCLUDE_SCHEMA': False,
        },
        STATIC_URL='/static/',
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    )
    django.setup()

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        app_label = '__main__'

    def __str__(self) -> str:
        return self.title

class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')

    class Meta:
        app_label = '__main__'

    def __str__(self) -> str:
        return f"{self.user.username} borrowed {self.book.title}"

class Payment(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'

    class TypeChoices(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment'
        FINE = 'FINE', 'Fine'

    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    type = models.CharField(max_length=10, choices=TypeChoices.choices)
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    session_url = models.URLField(max_length=500, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    money_to_pay = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        app_label = '__main__'

    def __str__(self) -> str:
        return f"{self.type} for {self.borrowing}"

admin.site.register(Book)
admin.site.register(Borrowing)
admin.site.register(Payment)

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class BorrowingSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Borrowing
        fields = ['id', 'borrow_date', 'expected_return_date', 'actual_return_date', 'book', 'user', 'payments']
        read_only_fields = ['borrow_date', 'actual_return_date', 'user']

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        book = attrs.get('book')
        if book and book.inventory <= 0:
            raise serializers.ValidationError({"book": "This book is currently out of stock."})
        return attrs

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> Any:
        book = validated_data['book']
        book.inventory -= 1
        book.save()

        borrowing = super().create(validated_data)

        days = (borrowing.expected_return_date - date.today()).days
        days = max(days, 1)
        money_to_pay = Decimal(days) * book.daily_fee

        Payment.objects.create(
            status=Payment.StatusChoices.PENDING,
            type=Payment.TypeChoices.PAYMENT,
            borrowing=borrowing,
            money_to_pay=money_to_pay,
            session_url="https://example.com/pay",
            session_id="mock_session_id"
        )

        return borrowing

class BorrowingReturnSerializer(serializers.Serializer):
    pass

class BorrowingFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter(field_name='actual_return_date', lookup_expr='isnull')
    actual_return_date = django_filters.DateFilter(field_name='actual_return_date')

    class Meta:
        model = Borrowing
        fields = ['user', 'is_active', 'actual_return_date']

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['title', 'author']

class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BorrowingFilter

    def get_queryset(self) -> Any:
        user = self.request.user
        if user.is_staff:
            return Borrowing.objects.all()
        return Borrowing.objects.filter(user=user)

    def perform_create(self, serializer: serializers.Serializer) -> None:
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], serializer_class=BorrowingReturnSerializer)
    @transaction.atomic
    def return_book(self, request: Request, pk: Optional[int] = None) -> Response:
        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            return Response(
                {"detail": "Book already returned."},
                status=status.HTTP_400_BAD_REQUEST
            )

        borrowing.actual_return_date = date.today()
        borrowing.save()

        borrowing.book.inventory += 1
        borrowing.book.save()

        if borrowing.actual_return_date > borrowing.expected_return_date:
            overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
            fine_multiplier = Decimal('2.0')
            fine_amount = Decimal(overdue_days) * borrowing.book.daily_fee * fine_multiplier

            Payment.objects.create(
                status=Payment.StatusChoices.PENDING,
                type=Payment.TypeChoices.FINE,
                borrowing=borrowing,
                money_to_pay=fine_amount,
                session_url="https://example.com/pay/fine",
                session_id="mock_fine_session_id"
            )

        return Response(
            {"detail": "Book returned successfully."},
            status=status.HTTP_200_OK
        )

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'type']

    def get_queryset(self) -> Any:
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(borrowing__user=user)

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'borrowings', BorrowingViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/doc/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if __name__ == '__main__':
    if len(sys.argv) == 1:
        django.core.management.call_command('migrate', run_syncdb=True, verbosity=0, interactive=False)
        sys.argv.extend(['runserver', '0.0.0.0:8000'])
    execute_from_command_line(sys.argv)