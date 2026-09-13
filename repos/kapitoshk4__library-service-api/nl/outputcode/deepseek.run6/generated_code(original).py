# filename: requirements.txt
Django>=3.2,<4.0
djangorestframework
djangorestframework-simplejwt
drf-yasg
django-filter
Pillow

# filename: manage.py
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()

# filename: library_service/__init__.py
# (empty)

# filename: library_service/settings.py
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-placeholder-key-change-in-production'
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
    'drf_yasg',
    'django_filters',
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
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}

# filename: library_service/wsgi.py
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_wsgi_application()

# filename: library_service/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Library Service API",
        default_version='v1',
        description="API for borrowing books",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('library.urls')),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/doc/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/v1/doc/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# filename: library/__init__.py
# (empty)

# filename: library/models.py
from django.db import models
from django.contrib.auth.models import User
from datetime import date
from decimal import Decimal

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.ImageField(upload_to='covers/', blank=True, null=True)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2, help_text="Daily borrowing fee in dollars")
    fine_per_day = models.DecimalField(max_digits=6, decimal_places=2, help_text="Overdue fine per day in dollars")

    def __str__(self):
        return self.title

    def is_available(self):
        """Check if no active borrowing exists (actual_return_date is null)"""
        active_borrowings = self.borrowings.filter(actual_return_date__isnull=True)
        return not active_borrowings.exists()

class Borrowing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-borrow_date']

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.borrow_date})"

    def save(self, *args, **kwargs):
        # Automatically set expected return date if not provided (e.g., 30 days)
        if not self.expected_return_date:
            self.expected_return_date = self.borrow_date + timedelta(days=30)
        super().save(*args, **kwargs)

    def return_book(self):
        """Set actual return date and deactivate borrowing"""
        if self.actual_return_date is not None:
            raise ValueError("Book already returned")
        self.actual_return_date = date.today()
        self.is_active = False
        self.save()

    @property
    def is_overdue(self):
        """Check if book is still active and past expected return date"""
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return date.today() > self.expected_return_date

class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('BORROWING', 'Borrowing Fee'),
        ('FINE', 'Fine'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
    )

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_type} - {self.amount} ({self.status})"

# filename: library/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Book, Borrowing, Payment
from datetime import date

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class BorrowingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    book = BookSerializer(read_only=True)
    total_fee = serializers.SerializerMethodField()
    fine_amount = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = ('id', 'user', 'book', 'borrow_date', 'expected_return_date',
                  'actual_return_date', 'is_active', 'total_fee', 'fine_amount')

    def get_total_fee(self, obj):
        # Sum of all payments for this borrowing
        return sum(payment.amount for payment in obj.payments.all())

    def get_fine_amount(self, obj):
        # Sum of fine payments
        return sum(payment.amount for payment in obj.payments.filter(payment_type='FINE'))

class BorrowingCreateSerializer(serializers.ModelSerializer):
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(), source='book', write_only=True
    )

    class Meta:
        model = Borrowing
        fields = ('book_id',)

    def validate_book(self, book):
        if not book.is_available():
            raise serializers.ValidationError("Book is not available for borrowing")
        return book

    def create(self, validated_data):
        user = self.context['request'].user
        book = validated_data['book']
        borrowing = Borrowing.objects.create(
            user=user,
            book=book,
            borrow_date=date.today(),
            expected_return_date=date.today() + timedelta(days=30),
        )
        # Create payment for borrowing fee
        fee = book.daily_fee * (borrowing.expected_return_date - borrowing.borrow_date).days
        Payment.objects.create(
            borrowing=borrowing,
            amount=fee,
            payment_type='BORROWING',
        )
        return borrowing

class ReturnSerializer(serializers.Serializer):
    # No fields needed, just trigger return action
    pass

# filename: library/filters.py
import django_filters
from .models import Borrowing, Book

class BorrowingFilter(django_filters.FilterSet):
    user_id = django_filters.NumberFilter(field_name='user_id')
    actual_return_date = django_filters.DateFromToRangeFilter(field_name='actual_return_date')

    class Meta:
        model = Borrowing
        fields = ['user_id', 'actual_return_date', 'is_active']

# filename: library/views.py
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingSerializer,
    BorrowingCreateSerializer,
    ReturnSerializer,
    PaymentSerializer,
)
from .filters import BorrowingFilter
from datetime import date
from decimal import Decimal

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['title', 'author']

class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BorrowingFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return BorrowingCreateSerializer
        if self.action == 'return_book':
            return ReturnSerializer
        return BorrowingSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(request_body=ReturnSerializer)
    @action(detail=True, methods=['post'], url_path='return')
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.actual_return_date is not None:
            return Response(
                {'detail': 'Book already returned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Perform return
        borrowing.actual_return_date = date.today()
        borrowing.is_active = False
        borrowing.save()

        # Check if overdue and create fine if needed
        if borrowing.actual_return_date > borrowing.expected_return_date:
            overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
            fine_amount = borrowing.book.fine_per_day * overdue_days
            # Ensure no duplicate fine
            if not borrowing.payments.filter(payment_type='FINE').exists():
                Payment.objects.create(
                    borrowing=borrowing,
                    amount=fine_amount,
                    payment_type='FINE',
                )
        return Response(BorrowingSerializer(borrowing).data)

    def list(self, request, *args, **kwargs):
        # Users can see only their own borrowings unless admin
        queryset = self.filter_queryset(self.get_queryset())
        if not request.user.is_staff:
            queryset = queryset.filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(borrowing__user=self.request.user)
        return queryset

# filename: library/urls.py
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

# filename: library/admin.py
from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'daily_fee', 'fine_per_day')
    search_fields = ('title', 'author')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_active')
    list_filter = ('is_active', 'actual_return_date', 'user')
    search_fields = ('user__username', 'book__title')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('borrowing', 'amount', 'payment_type', 'status', 'created_at')
    list_filter = ('payment_type', 'status', 'created_at')