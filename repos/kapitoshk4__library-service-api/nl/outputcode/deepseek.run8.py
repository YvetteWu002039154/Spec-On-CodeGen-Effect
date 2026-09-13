# File: manage.py
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_project.settings')
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

# File: library_project/__init__.py
# (empty)

# File: library_project/settings.py
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-me-in-production'

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

ROOT_URLCONF = 'library_project.urls'

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

WSGI_APPLICATION = 'library_project.wsgi.application'

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
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
}

# Fine multiplier: overdue daily fee * 2
FINE_MULTIPLIER = 2

# File: library_project/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Library Service API",
        default_version='v1',
        description="API for library book borrowings",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/doc/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/v1/doc/swagger<path:format>', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]

# File: library_project/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_project.settings')
application = get_wsgi_application()

# File: api/__init__.py
# (empty)

# File: api/models.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from datetime import date

class Book(models.Model):
    class CoverType(models.TextChoices):
        HARD = 'HARD', 'Hard'
        SOFT = 'SOFT', 'Soft'

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=CoverType.choices)
    inventory = models.PositiveIntegerField(default=0)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.title} by {self.author}"

    def clean(self):
        if self.daily_fee <= 0:
            raise ValidationError("Daily fee must be positive")

class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='borrowings')

    def __str__(self):
        return f"{self.user} borrowed {self.book.title} on {self.borrow_date}"

    def clean(self):
        if self.expected_return_date <= self.borrow_date:
            raise ValidationError("Expected return date must be after borrow date")
        if hasattr(self, 'book') and self.book.inventory <= 0:
            raise ValidationError("Book is out of stock")

    def save(self, *args, **kwargs):
        # Perform validation before saving
        self.full_clean()
        if not self.pk:  # on creation
            if self.book.inventory <= 0:
                raise ValidationError("Cannot borrow: book inventory is zero")
            self.book.inventory -= 1
            self.book.save()
        super().save(*args, **kwargs)

    def return_book(self):
        if self.actual_return_date is not None:
            raise ValidationError("Book already returned")
        self.actual_return_date = date.today()
        self.save()
        self.book.inventory += 1
        self.book.save()
        # Check overdue and create fine payment if needed
        if self.actual_return_date > self.expected_return_date:
            overdue_days = (self.actual_return_date - self.expected_return_date).days
            fine_amount = overdue_days * self.book.daily_fee * settings.FINE_MULTIPLIER
            Payment.objects.create(
                borrowing=self,
                money_to_pay=fine_amount,
                payment_type=Payment.PaymentType.FINE,
                status=Payment.PaymentStatus.PENDING,
                session_url=f"https://checkout.stripe.com/pay/cs_test_fine_{self.id}",
                session_id=f"cs_test_fine_{self.id}"
            )

class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'

    class PaymentType(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment'
        FINE = 'FINE', 'Fine'

    status = models.CharField(max_length=7, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_type = models.CharField(max_length=7, choices=PaymentType.choices)
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    session_url = models.URLField(max_length=512)
    session_id = models.CharField(max_length=255)
    money_to_pay = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.payment_type} #{self.id} ({self.status})"

    def clean(self):
        if self.money_to_pay <= 0:
            raise ValidationError("Payment amount must be positive")

# File: api/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Book, Borrowing, Payment
from datetime import date
from django.conf import settings

User = get_user_model()

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'cover', 'inventory', 'daily_fee']

class BorrowingCreateSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())

    class Meta:
        model = Borrowing
        fields = ['book', 'expected_return_date']

    def validate(self, data):
        book = data['book']
        if book.inventory <= 0:
            raise serializers.ValidationError("Book is out of stock")
        if data['expected_return_date'] <= date.today():
            raise serializers.ValidationError("Expected return date must be in the future")
        return data

class BorrowingSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Borrowing
        fields = ['id', 'borrow_date', 'expected_return_date', 'actual_return_date', 'book', 'user']

class BorrowingReturnSerializer(serializers.Serializer):
    """ Empty serializer for return action, no input needed """
    pass

class PaymentSerializer(serializers.ModelSerializer):
    borrowing_id = serializers.IntegerField(source='borrowing.id', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'status', 'payment_type', 'borrowing_id', 'session_url', 'session_id', 'money_to_pay']

# File: api/views.py
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from datetime import date
from .models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer, BorrowingSerializer, BorrowingCreateSerializer,
    BorrowingReturnSerializer, PaymentSerializer
)
from .filters import BookFilter, BorrowingFilter, PaymentFilter

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticatedOrReadOnlyCustom]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookFilter

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]

class BorrowingViewSet(viewsets.GenericViewSet,
                       mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin):
    queryset = Borrowing.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = BorrowingFilter
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return BorrowingCreateSerializer
        elif self.action == 'return_book':
            return BorrowingReturnSerializer
        return BorrowingSerializer

    def get_queryset(self):
        # Non-admin users see only their own borrowings
        user = self.request.user
        if user.is_staff:
            return Borrowing.objects.all()
        return Borrowing.objects.filter(user=user)

    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        expected_return_date = serializer.validated_data['expected_return_date']
        user = self.request.user
        borrowing = serializer.save(
            borrow_date=date.today(),
            book=book,
            user=user
        )
        # Calculate payment
        borrowing_days = (expected_return_date - borrowing.borrow_date).days
        total_price = borrowing_days * book.daily_fee
        Payment.objects.create(
            borrowing=borrowing,
            money_to_pay=total_price,
            payment_type=Payment.PaymentType.PAYMENT,
            status=Payment.PaymentStatus.PENDING,
            session_url=f"https://checkout.stripe.com/pay/cs_test_{borrowing.id}",
            session_id=f"cs_test_{borrowing.id}"
        )

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.user != request.user and not request.user.is_staff:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        try:
            borrowing.return_book()
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BorrowingSerializer(borrowing).data, status=status.HTTP_200_OK)

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaymentFilter

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(borrowing__user=user)

# Custom permission to allow read-only for unauthenticated, admin for write
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAuthenticatedOrReadOnlyCustom(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user and request.user.is_authenticated and request.user.is_staff

# File: api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, BorrowingViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'borrowings', BorrowingViewSet, basename='borrowing')
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

# File: api/admin.py
from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'cover', 'inventory', 'daily_fee']

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ['id', 'book', 'user', 'borrow_date', 'expected_return_date', 'actual_return_date']
    list_filter = ['actual_return_date', 'user']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment_type', 'status', 'borrowing', 'money_to_pay']

# File: api/filters.py
import django_filters
from .models import Book, Borrowing, Payment

class BookFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.CharFilter(lookup_expr='icontains')
    daily_fee__gte = django_filters.NumberFilter(field_name='daily_fee', lookup_expr='gte')
    daily_fee__lte = django_filters.NumberFilter(field_name='daily_fee', lookup_expr='lte')

    class Meta:
        model = Book
        fields = ['title', 'author', 'daily_fee__gte', 'daily_fee__lte']

class BorrowingFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='user_id')
    actual_return_date = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='exact')
    actual_return_date__gte = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='gte')
    actual_return_date__lte = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='lte')

    class Meta:
        model = Borrowing
        fields = ['user', 'actual_return_date', 'actual_return_date__gte', 'actual_return_date__lte']

class PaymentFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='borrowing__user_id')
    status = django_filters.ChoiceFilter(field_name='status', lookup_expr='exact')
    payment_type = django_filters.ChoiceFilter(field_name='payment_type', lookup_expr='exact')

    class Meta:
        model = Payment
        fields = ['user', 'status', 'payment_type']