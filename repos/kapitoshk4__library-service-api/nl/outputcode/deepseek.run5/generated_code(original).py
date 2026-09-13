# requirements.txt
Django==5.0.2
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.1
drf-spectacular==0.27.1
django-filter==23.5
# (optional) psycopg2-binary for PostgreSQL, but default sqlite3 used

# library_service/settings.py
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-library-secret-key-change-in-production'

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
    'drf_spectacular',
    'django_filters',
    'api',
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

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

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
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Library Service API',
    'DESCRIPTION': 'API for managing library borrowings and payments.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# library_service/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# library_service/wsgi.py
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_wsgi_application()

# library_service/asgi.py
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_asgi_application()

# manage.py
#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()

# api/__init__.py
# empty

# api/models.py
from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()

class Book(models.Model):
    COVER_CHOICES = [
        ('HARD', 'Hard'),
        ('SOFT', 'Soft'),
    ]
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=COVER_CHOICES)
    inventory = models.PositiveIntegerField(default=1)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return self.title

class Borrowing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.is_active = self.actual_return_date is None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

class Payment(models.Model):
    PENDING = 'PENDING'
    PAID = 'PAID'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
    ]
    RENTAL = 'RENTAL'
    FINE = 'FINE'
    TYPE_CHOICES = [
        (RENTAL, 'Rental Payment'),
        (FINE, 'Fine Payment'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.payment_type})"

# api/serializers.py
from rest_framework import serializers
from .models import Book, Borrowing, Payment
from django.utils import timezone
from datetime import date

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'cover', 'inventory', 'daily_fee']

class BorrowingSerializer(serializers.ModelSerializer):
    book_title = serializers.ReadOnlyField(source='book.title')
    user_email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = Borrowing
        fields = ['id', 'user', 'book', 'borrow_date', 'expected_return_date',
                  'actual_return_date', 'is_active', 'book_title', 'user_email']
        read_only_fields = ['user', 'actual_return_date', 'is_active']

    def validate(self, data):
        book = data['book']
        if book.inventory <= 0:
            raise serializers.ValidationError("Book is not available (inventory 0).")
        borrow_date = data['borrow_date']
        expected_return = data['expected_return_date']
        if expected_return < borrow_date:
            raise serializers.ValidationError("Expected return date cannot be before borrow date.")
        return data

    def create(self, validated_data):
        book = validated_data['book']
        user = self.context['request'].user
        # Decrement inventory
        book.inventory -= 1
        book.save()

        borrowing = Borrowing.objects.create(
            user=user,
            book=book,
            borrow_date=validated_data['borrow_date'],
            expected_return_date=validated_data['expected_return_date']
        )
        return borrowing

class ReturnBorrowingSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField(required=True)

    def validate_actual_return_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Return date cannot be in the future.")
        return value

class PaymentSerializer(serializers.ModelSerializer):
    borrowing_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'borrowing', 'amount', 'payment_date', 'payment_type', 'status', 'borrowing_id']
        read_only_fields = ['id', 'borrowing', 'amount', 'payment_date', 'payment_type', 'status']

    def validate(self, data):
        borrowing_id = data.pop('borrowing_id')
        try:
            borrowing = Borrowing.objects.get(id=borrowing_id)
        except Borrowing.DoesNotExist:
            raise serializers.ValidationError("Borrowing not found.")

        # Only active borrowings can have rental payment made.
        if not borrowing.is_active:
            raise serializers.ValidationError("Borrowing is already returned; cannot make rental payment.")

        # Check if a rental payment already exists for this borrowing
        if borrowing.payments.filter(payment_type='RENTAL').exists():
            raise serializers.ValidationError("Rental payment already exists for this borrowing.")

        data['borrowing'] = borrowing
        data['user'] = self.context['request'].user
        # Calculate rental amount
        days = (borrowing.expected_return_date - borrowing.borrow_date).days
        if days < 1:
            days = 1
        data['amount'] = borrowing.book.daily_fee * days
        data['payment_type'] = 'RENTAL'
        return data

    def create(self, validated_data):
        return Payment.objects.create(**validated_data)

# api/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user or request.user.is_staff

# api/filters.py
import django_filters
from .models import Borrowing

class BorrowingFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='user__id')
    actual_return_date_after = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='gte')
    actual_return_date_before = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='lte')

    class Meta:
        model = Borrowing
        fields = ['user', 'actual_return_date_after', 'actual_return_date_before']

# api/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Book, Borrowing, Payment
from .serializers import BookSerializer, BorrowingSerializer, ReturnBorrowingSerializer, PaymentSerializer
from .permissions import IsAdminOrOwner
from .filters import BorrowingFilter
from datetime import date

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author']
    ordering_fields = ['title', 'author']

class BorrowingViewSet(viewsets.ModelViewSet):
    serializer_class = BorrowingSerializer
    permission_classes = [IsAdminOrOwner]
    filterset_class = BorrowingFilter
    ordering_fields = ['borrow_date', 'expected_return_date', 'actual_return_date']

    def get_queryset(self):
        if self.request.user.is_staff:
            return Borrowing.objects.all()
        return Borrowing.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='return')
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if not borrowing.is_active:
            return Response({'detail': 'This borrowing has already been returned.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReturnBorrowingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actual_return_date = serializer.validated_data['actual_return_date']

        borrowing.actual_return_date = actual_return_date
        borrowing.save()

        # Return book to inventory
        book = borrowing.book
        book.inventory += 1
        book.save()

        # Create fine payment if overdue
        if actual_return_date > borrowing.expected_return_date:
            overdue_days = (actual_return_date - borrowing.expected_return_date).days
            fine_amount = book.daily_fee * overdue_days * 2  # doubled daily fee as fine
            Payment.objects.create(
                user=borrowing.user,
                borrowing=borrowing,
                amount=fine_amount,
                payment_type='FINE',
                status='PENDING'
            )

        return Response(BorrowingSerializer(borrowing, context={'request': request}).data)

class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import BookViewSet, BorrowingViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'borrowings', BorrowingViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]

# api/admin.py
from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'cover', 'inventory', 'daily_fee')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_active')
    list_filter = ('is_active', 'actual_return_date')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'borrowing', 'amount', 'payment_type', 'status', 'payment_date')
    list_filter = ('payment_type', 'status')