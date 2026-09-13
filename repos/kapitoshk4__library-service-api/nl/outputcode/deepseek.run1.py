"""manage.py"""
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_service.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

"""library_service/__init__.py"""
# empty

"""library_service/settings.py"""
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-&%#@s7x(8k_v9@l=u0o)4+6$nl!2f!wq=)b+*1q7#e5zw@x#r!'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
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
    'library',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'library_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'library_service.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Library Service API',
    'DESCRIPTION': 'API for managing books, borrowings and payments',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

"""library_service/urls.py"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('library.urls')),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

"""library_service/wsgi.py"""
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_wsgi_application()

"""library/__init__.py"""
# empty

"""library/models.py"""
from django.db import models
from django.conf import settings
from django.utils import timezone

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    inventory = models.PositiveIntegerField(default=0)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.title} by {self.author}"

class Borrowing(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateTimeField(default=timezone.now)
    expected_return_date = models.DateTimeField()
    actual_return_date = models.DateTimeField(null=True, blank=True)

    @property
    def is_overdue(self) -> bool:
        """Check if borrowing is overdue (actual return > expected)."""
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return timezone.now() > self.expected_return_date

    @property
    def overdue_days(self) -> int:
        if self.actual_return_date:
            return (self.actual_return_date - self.expected_return_date).days
        else:
            return (timezone.now().date() - self.expected_return_date.date()).days

class Payment(models.Model):
    class PaymentType(models.TextChoices):
        BORROW = 'BORROW', 'Borrowing payment'
        FINE = 'FINE', 'Fine payment'

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_type = models.CharField(max_length=10, choices=PaymentType.choices)
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_date = models.DateTimeField(null=True, blank=True)

    def mark_paid(self):
        self.status = Payment.PaymentStatus.PAID
        self.payment_date = timezone.now()
        self.save()

"""library/admin.py"""
from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'inventory', 'daily_fee')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'borrowing', 'amount', 'payment_type', 'status', 'payment_date')

"""library/filters.py"""
import django_filters
from .models import Borrowing, Book, Payment

class BorrowingFilter(django_filters.FilterSet):
    actual_return_date = django_filters.DateFilter()
    actual_return_date__gte = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='gte')
    actual_return_date__lte = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='lte')
    user = django_filters.NumberFilter(field_name='user_id')

    class Meta:
        model = Borrowing
        fields = ['actual_return_date', 'actual_return_date__gte', 'actual_return_date__lte', 'user']

class BookFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Book
        fields = ['title', 'author']

class PaymentFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='user_id')
    status = django_filters.ChoiceFilter(choices=Payment.PaymentStatus.choices)
    payment_type = django_filters.ChoiceFilter(choices=Payment.PaymentType.choices)

    class Meta:
        model = Payment
        fields = ['user', 'status', 'payment_type']

"""library/serializers.py"""
from rest_framework import serializers
from .models import Book, Borrowing, Payment
from django.utils import timezone
from decimal import Decimal
import datetime

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'inventory', 'daily_fee']
        read_only_fields = ['id']

class BorrowingSerializer(serializers.ModelSerializer):
    book_title = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = [
            'id', 'user', 'book', 'borrow_date', 'expected_return_date',
            'actual_return_date', 'book_title', 'user_email'
        ]
        read_only_fields = ['id', 'user', 'borrow_date', 'book_title', 'user_email']

    def get_book_title(self, obj):
        return obj.book.title

    def get_user_email(self, obj):
        return obj.user.email

class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ['book', 'expected_return_date']

    def validate(self, attrs):
        book = attrs['book']
        if book.inventory < 1:
            raise serializers.ValidationError("This book is currently out of stock.")
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        book = validated_data['book']
        expected_return_date = validated_data['expected_return_date']
        borrow_date = timezone.now()

        # create borrowing
        borrowing = Borrowing.objects.create(
            user=user,
            book=book,
            borrow_date=borrow_date,
            expected_return_date=expected_return_date,
            actual_return_date=None
        )

        # reduce inventory
        book.inventory -= 1
        book.save()

        # create initial payment (borrowing fee)
        days = (expected_return_date.date() - borrow_date.date()).days
        amount = book.daily_fee * days
        Payment.objects.create(
            user=user,
            borrowing=borrowing,
            amount=amount,
            payment_type=Payment.PaymentType.BORROW,
            status=Payment.PaymentStatus.PENDING
        )

        return borrowing

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'user', 'borrowing', 'amount', 'payment_type', 'status', 'payment_date']
        read_only_fields = ['id', 'user', 'amount', 'payment_type']

class PaymentPaySerializer(serializers.Serializer):
    pass  # No fields needed; just triggers the action

"""library/views.py"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from .models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingSerializer,
    BorrowingCreateSerializer,
    PaymentSerializer,
    PaymentPaySerializer
)
from .filters import BookFilter, BorrowingFilter, PaymentFilter

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_staff

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = BookFilter
    search_fields = ['title', 'author']
    ordering_fields = ['title', 'author', 'daily_fee']

class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    filterset_class = BorrowingFilter
    search_fields = ['book__title', 'user__email']
    ordering_fields = ['borrow_date', 'expected_return_date', 'actual_return_date']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()
        return Borrowing.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return BorrowingCreateSerializer
        return BorrowingSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # already handled in serializer

    @action(detail=True, methods=['post'], url_path='return')
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.actual_return_date is not None:
            return Response({"detail": "This book has already been returned."},
                            status=status.HTTP_400_BAD_REQUEST)

        # set actual return date to now (or can be provided in request, but for simplicity now)
        actual_date = timezone.now()
        borrowing.actual_return_date = actual_date
        borrowing.save()

        # increase inventory
        book = borrowing.book
        book.inventory += 1
        book.save()

        # check overdue and create fine payment if needed
        if borrowing.is_overdue:
            overdue_days = borrowing.overdue_days
            fine_amount = book.daily_fee * overdue_days * 2  # multiplier 2 for fine
            Payment.objects.create(
                user=borrowing.user,
                borrowing=borrowing,
                amount=fine_amount,
                payment_type=Payment.PaymentType.FINE,
                status=Payment.PaymentStatus.PENDING
            )

        return Response(BorrowingSerializer(borrowing).data)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filterset_class = PaymentFilter
    search_fields = ['borrowing__book__title', 'user__email']
    ordering_fields = ['amount', 'payment_date', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()
        return Payment.objects.filter(user=user)

    def get_serializer_class(self):
        if self.action == 'pay':
            return PaymentPaySerializer
        return PaymentSerializer

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        payment = self.get_object()
        if payment.status != Payment.PaymentStatus.PENDING:
            return Response({"detail": "This payment is not pending."},
                            status=status.HTTP_400_BAD_REQUEST)
        payment.mark_paid()
        return Response(PaymentSerializer(payment).data)

"""library/urls.py"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, BorrowingViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'borrowings', BorrowingViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]