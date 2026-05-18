#!/usr/bin/env python3
"""
Library Service API - Complete Implementation
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Django settings configuration
DJANGO_SETTINGS = {
    'DEBUG': True,
    'SECRET_KEY': 'library-service-secret-key-change-in-production',
    'ALLOWED_HOSTS': ['*'],
    'INSTALLED_APPS': [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'rest_framework',
        'rest_framework_simplejwt',
        'drf_spectacular',
        'corsheaders',
        'books',
        'borrowings',
        'payments',
        'users',
    ],
    'MIDDLEWARE': [
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'corsheaders.middleware.CorsMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ],
    'ROOT_URLCONF': 'library_service.urls',
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'library_service.db',
        }
    },
    'AUTH_USER_MODEL': 'users.User',
    'REST_FRAMEWORK': {
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework_simplejwt.authentication.JWTAuthentication',
        ],
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
        ],
        'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    },
    'SPECTACULAR_SETTINGS': {
        'TITLE': 'Library Service API',
        'DESCRIPTION': 'API Library service for borrowing books',
        'VERSION': '1.0.0',
        'SERVE_INCLUDE_SCHEMA': False,
    },
    'SIMPLE_JWT': {
        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
        'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    },
    'STATIC_URL': '/static/',
    'TEMPLATES': [
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
    ],
    'CORS_ALLOW_ALL_ORIGINS': True,
    'FINE_MULTIPLIER': Decimal('2.0'),
}

# Write settings to file
settings_content = '''
import os
from decimal import Decimal
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'library-service-secret-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

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
    'corsheaders',
    'books',
    'borrowings',
    'payments',
    'users',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
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
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', BASE_DIR / 'library_service.db'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }
}

AUTH_USER_MODEL = 'users.User'

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

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Library Service API',
    'DESCRIPTION': 'API Library service for borrowing books written on DRF',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

CORS_ALLOW_ALL_ORIGINS = True

FINE_MULTIPLIER = Decimal('2.0')

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_placeholder')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_placeholder')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

DOMAIN_URL = os.environ.get('DOMAIN_URL', 'http://localhost:8000')
'''

# Write all necessary files
import os

def create_directory(path):
    os.makedirs(path, exist_ok=True)

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

# Create project structure
create_directory('library_service')
create_directory('books')
create_directory('borrowings')
create_directory('payments')
create_directory('users')

# Write settings
write_file('library_service/settings.py', settings_content)

# Write main URLs
urls_content = '''
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/doc/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/doc/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/v1/books/', include('books.urls')),
    path('api/v1/borrowings/', include('borrowings.urls')),
    path('api/v1/payments/', include('payments.urls')),
    path('api/v1/users/', include('users.urls')),
]
'''
write_file('library_service/urls.py', urls_content)

# Write wsgi
wsgi_content = '''
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_wsgi_application()
'''
write_file('library_service/wsgi.py', wsgi_content)

# Write asgi
asgi_content = '''
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_asgi_application()
'''
write_file('library_service/asgi.py', asgi_content)

write_file('library_service/__init__.py', '')

# Users app
users_models = '''
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['email']
    
    def __str__(self):
        return self.email
    
    @property
    def is_admin(self):
        return self.is_staff or self.is_superuser
'''
write_file('users/models.py', users_models)

users_serializers = '''
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'password', 'is_staff')
        read_only_fields = ('id', 'is_staff')
    
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'is_staff')
        read_only_fields = ('id', 'is_staff')


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['is_staff'] = user.is_staff
        return token
'''
write_file('users/serializers.py', users_serializers)

users_views = '''
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema, extend_schema_view

from .serializers import UserSerializer, UserDetailSerializer, CustomTokenObtainPairSerializer

User = get_user_model()


@extend_schema(tags=['Users'])
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary='Register a new user',
        description='Create a new user account with email and password',
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=['Users'])
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    @extend_schema(summary='Get current user profile')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(summary='Update current user profile')
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(summary='Partially update current user profile')
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


@extend_schema(tags=['Authentication'])
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
    @extend_schema(
        summary='Obtain JWT token pair',
        description='Get access and refresh tokens using email and password',
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
'''
write_file('users/views.py', users_views)

users_urls = '''
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import CreateUserView, ManageUserView, CustomTokenObtainPairView

urlpatterns = [
    path('register/', CreateUserView.as_view(), name='user-register'),
    path('me/', ManageUserView.as_view(), name='user-me'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token-verify'),
]
'''
write_file('users/urls.py', users_urls)

users_admin = '''
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )
'''
write_file('users/admin.py', users_admin)

write_file('users/__init__.py', '')
write_file('users/apps.py', '''
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
''')

# Books app
books_models = '''
from django.db import models


class Book(models.Model):
    class CoverType(models.TextChoices):
        HARD = 'HARD', 'Hard'
        SOFT = 'SOFT', 'Soft'
    
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=10, choices=CoverType.choices, default=CoverType.SOFT)
    inventory = models.PositiveIntegerField(default=0)
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = 'Book'
        verbose_name_plural = 'Books'
        ordering = ['title']
    
    def __str__(self):
        return f"{self.title} by {self.author}"
    
    @property
    def is_available(self):
        return self.inventory > 0
    
    def borrow(self):
        if self.inventory <= 0:
            raise ValueError("Book is not available for borrowing")
        self.inventory -= 1
        self.save()
    
    def return_book(self):
        self.inventory += 1
        self.save()
'''
write_file('books/models.py', books_models)

books_serializers = '''
from rest_framework import serializers
from .models import Book


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'cover', 'inventory', 'daily_fee')
        read_only_fields = ('id',)
    
    def validate_inventory(self, value):
        if value < 0:
            raise serializers.ValidationError("Inventory cannot be negative")
        return value
    
    def validate_daily_fee(self, value):
        if value <= 0:
            raise serializers.ValidationError("Daily fee must be positive")
        return value


class BookListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'cover', 'inventory', 'daily_fee')
        read_only_fields = ('id',)
'''
write_file('books/serializers.py', books_serializers)

books_views = '''
from rest_framework import viewsets, permissions, filters
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Book
from .serializers import BookSerializer, BookListSerializer
from .permissions import IsAdminOrReadOnly


@extend_schema_view(
    list=extend_schema(
        summary='List all books',
        description='Get a list of all available books in the library',
        parameters=[
            OpenApiParameter(
                name='title',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by book title',
            ),
            OpenApiParameter(
                name='author',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by book author',
            ),
            OpenApiParameter(
                name='cover',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by cover type (HARD/SOFT)',
            ),
        ],
        tags=['Books'],
    ),
    create=extend_schema(
        summary='Create a new book',
        description='Admin only: Create a new book in the library',
        tags=['Books'],
    ),
    retrieve=extend_schema(
        summary='Get book details',
        description='Get detailed information about a specific book',
        tags=['Books'],
    ),
    update=extend_schema(
        summary='Update a book',
        description='Admin only: Update book information',
        tags=['Books'],
    ),
    partial_update=extend_schema(
        summary='Partially update a book',
        description='Admin only: Partially update book information',
        tags=['Books'],
    ),
    destroy=extend_schema(
        summary='Delete a book',
        description='Admin only: Delete a book from the library',
        tags=['Books'],
    ),
)
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author']
    ordering_fields = ['title', 'author', 'daily_fee', 'inventory']
    ordering = ['title']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BookListSerializer
        return BookSerializer
    
    def get_queryset(self):
        queryset = Book.objects.all()
        title = self.request.query_params.get('title')
        author = self.request.query_params.get('author')
        cover = self.request.query_params.get('cover')
        
        if title:
            queryset = queryset.filter(title__icontains=title)
        if author:
            queryset = queryset.filter(author__icontains=author)
        if cover:
            queryset = queryset.filter(cover=cover.upper())
        
        return queryset
'''
write_file('books/views.py', books_views)

books_permissions = '''
from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit books.
    Read-only access is allowed for any authenticated user.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
'''
write_file('books/permissions.py', books_permissions)

books_urls = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import BookViewSet

router = DefaultRouter()
router.register('', BookViewSet, basename='book')

urlpatterns = [
    path('', include(router.urls)),
]
'''
write_file('books/urls.py', books_urls)

books_admin = '''
from django.contrib import admin
from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'cover', 'inventory', 'daily_fee')
    list_filter = ('cover',)
    search_fields = ('title', 'author')
    ordering = ('title',)
    list_editable = ('inventory', 'daily_fee')
'''
write_file('books/admin.py', books_admin)

write_file('books/__init__.py', '')
write_file('books/apps.py', '''
from django.apps import AppConfig


class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'books'
''')

# Payments app
payments_models = '''
from django.db import models
from django.conf import settings


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        EXPIRED = 'EXPIRED', 'Expired'
    
    class Type(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment'
        FINE = 'FINE', 'Fine'
    
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        default=Type.PAYMENT
    )
    borrowing = models.ForeignKey(
        'borrowings.Borrowing',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    session_url = models.URLField(max_length=500, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-id']
    
    def __str__(self):
        return f"Payment #{self.id} - {self.type} - {self.status} - ${self.money_to_pay}"
    
    @property
    def is_paid(self):
        return self.status == self.Status.PAID
    
    @property
    def is_pending(self):
        return self.status == self.Status.PENDING
'''
write_file('payments/models.py', payments_models)

payments_serializers = '''
from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    borrowing_id = serializers.IntegerField(source='borrowing.id', read_only=True)
    
    class Meta:
        model = Payment
        fields = (
            'id',
            'status',
            'type',
            'borrowing_id',
            'session_url',
            'session_id',
            'money_to_pay',
        )
        read_only_fields = ('id', 'session_url', 'session_id', 'money_to_pay', 'status', 'type')


class PaymentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'status', 'type', 'borrowing', 'money_to_pay')
        read_only_fields = ('id',)


class PaymentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            'id',
            'status',
            'type',
            'borrowing',
            'session_url',
            'session_id',
            'money_to_pay',
        )
        read_only_fields = ('id',)
'''
write_file('payments/serializers.py', payments_serializers)

payments_views = '''
from decimal import Decimal
from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Payment
from .serializers import PaymentSerializer, PaymentListSerializer, PaymentDetailSerializer


@extend_schema_view(
    list=extend_schema(
        summary='List all payments',
        description='Get a list of payments. Admins see all payments, users see only their own.',
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by payment status (PENDING/PAID/EXPIRED)',
            ),
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by payment type (PAYMENT/FINE)',
            ),
        ],
        tags=['Payments'],
    ),
    retrieve=extend_schema(
        summary='Get payment details',
        description='Get detailed information about a specific payment',
        tags=['Payments'],
    ),
    success=extend_schema(
        summary='Payment success callback',
        description='Handle successful payment from Stripe',
        tags=['Payments'],
    ),
    cancel=extend_schema(
        summary='Payment cancel callback',
        description='Handle cancelled payment from Stripe',
        tags=['Payments'],
    ),
)
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PaymentListSerializer
        return PaymentDetailSerializer
    
    def get_queryset(self):
        queryset = Payment.objects.select_related('borrowing', 'borrowing__user', 'borrowing__book')
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(borrowing__user=self.request.user)
        
        status_filter = self.request.query_params.get('status')
        type_filter = self.request.query_params.get('type')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        if type_filter:
            queryset = queryset.filter(type=type_filter.upper())
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='success')
    def success(self, request):
        session_id = request.query_params.get('session_id')
        
        if not session_id:
            return Response(
                {'error': 'session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment = Payment.objects.get(session_id=session_id)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # In production, verify with Stripe
        # stripe.checkout.Session.retrieve(session_id)
        payment.status = Payment.Status.PAID
        payment.save()
        
        serializer = PaymentDetailSerializer(payment)
        return Response({
            'message': 'Payment successful!',
            'payment': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='cancel')
    def cancel(self, request):
        session_id = request.query_params.get('session_id')
        
        return Response({
            'message': 'Payment was cancelled. You can pay later within 24 hours.',
            'session_id': session_id,
        })
    
    @action(detail=True, methods=['post'], url_path='renew')
    def renew(self, request, pk=None):
        payment = self.get_object()
        
        if payment.status != Payment.Status.EXPIRED:
            return Response(
                {'error': 'Only expired payments can be renewed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new Stripe session (simplified)
        domain_url = getattr(settings, 'DOMAIN_URL', 'http://localhost:8000')
        
        payment.status = Payment.Status.PENDING
        payment.session_url = f"{domain_url}/api/v1/payments/success/?session_id={payment.session_id}"
        payment.save()
        
        serializer = PaymentDetailSerializer(payment)
        return Response(serializer.data)
'''
write_file('payments/views.py', payments_views)

payments_urls = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet

router = DefaultRouter()
router.register('', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
]
'''
write_file('payments/urls.py', payments_urls)

payments_admin = '''
from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'type', 'borrowing', 'money_to_pay', 'session_id')
    list_filter = ('status', 'type')
    search_fields = ('session_id', 'borrowing__user__email')
    ordering = ('-id',)
    readonly_fields = ('session_url', 'session_id')
'''
write_file('payments/admin.py', payments_admin)

write_file('payments/__init__.py', '')
write_file('payments/apps.py', '''
from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
''')

# Borrowings app
borrowings_models = '''
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class Borrowing(models.Model):
    borrow_date = models.DateField(default=timezone.now)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.CASCADE,
        related_name='borrowings'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='borrowings'
    )
    
    class Meta:
        verbose_name = 'Borrowing'
        verbose_name_plural = 'Borrowings'
        ordering = ['-borrow_date']
    
    def __str__(self):
        return f"Borrowing #{self.id} - {self.book.title} by {self.user.email}"
    
    @property
    def is_active(self):
        return self.actual_return_date is None
    
    @property
    def is_overdue(self):
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return timezone.now().date() > self.expected_return_date
    
    @property
    def days_borrowed(self):
        end_date = self.actual_return_date or timezone.now().date()
        return (end_date - self.borrow_date).days
    
    @property
    def overdue_days(self):
        if not self.is_overdue:
            return 0
        end_date = self.actual_return_date or timezone.now().date()
        return (end_date - self.expected_return_date).days
    
    def calculate_payment_amount(self):
        days = (self.expected_return_date - self.borrow_date).days
        return Decimal(str(days)) * self.book.daily_fee
    
    def calculate_fine_amount(self):
        if not self.is_overdue:
            return Decimal('0.00')
        fine_multiplier = getattr(settings, 'FINE_MULTIPLIER', Decimal('2.0'))
        return Decimal(str(self.overdue_days)) * self.book.daily_fee * fine_multiplier
    
    def return_book(self):
        from django.utils import timezone
        if self.actual_return_date is not None:
            raise ValueError("Book has already been returned")
        self.actual_return_date = timezone.now().date()
        self.book.return_book()
        self.save()
'''
write_file('borrowings/models.py', borrowings_models)

borrowings_serializers = '''
from datetime import date
from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers

from books.serializers import BookSerializer
from books.models import Book
from payments.models import Payment
from .models import Borrowing


class PaymentNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'status', 'type', 'money_to_pay', 'session_url')


class BorrowingSerializer(serializers.ModelSerializer):
    payments = PaymentNestedSerializer(many=True, read_only=True)
    
    class Meta:
        model = Borrowing
        fields = (
            'id',
            'borrow_date',
            'expected_return_date',
            'actual_return_date',
            'book',
            'user',
            'payments',
        )
        read_only_fields = ('id', 'borrow_date', 'actual_return_date', 'user')
    
    def validate(self, attrs):
        expected_return_date = attrs.get('expected_return_date')
        borrow_date = date.today()
        
        if expected_return_date and expected_return_date <= borrow_date:
            raise serializers.ValidationError(
                "Expected return date must be after borrow date"
            )
        
        book = attrs.get('book')
        if book and not book.is_available:
            raise serializers.ValidationError(
                f"Book '{book.title}' is not available for borrowing"
            )
        
        return attrs


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ('id', 'expected_return_date', 'book')
        read_only_fields = ('id',)
    
    def validate(self, attrs):
        expected_return_date = attrs.get('expected_return_date')
        borrow_date = date.today()
        
        if expected_return_date and expected_return_date <= borrow_date:
            raise serializers.ValidationError(
                "Expected return date must be after borrow date"
            )
        
        book = attrs.get('book')
        if book and not book.is_available:
            raise serializers.ValidationError(
                f"Book '{book.title}' is not available for borrowing"
            )
        
        return attrs
    
    def create(self, validated_data):
        book = validated_data['book']
        book.borrow()
        
        borrowing = Borrowing.objects.create(
            user=self.context['request'].user,
            **validated_data
        )
        
        # Create payment for borrowing
        payment_amount = borrowing.calculate_payment_amount()
        domain_url = 'http://localhost:8000'
        
        Payment.objects.create(
            borrowing=borrowing,
            type=Payment.Type.PAYMENT,
            status=Payment.Status.PENDING,
            money_to_pay=payment_amount,
            session_url=f"{domain_url}/api/v1/payments/success/?session_id=session_{borrowing.id}",
            session_id=f"session_{borrowing.id}",
        )
        
        return borrowing


class BorrowingListSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Borrowing
        fields = (
            'id',
            'borrow_date',
            'expected_return_date',
            'actual_return_date',
            'book',
            'book_title',
            'user',
            'user_email',
        )
        read_only_fields = ('id',)


class BorrowingDetailSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    payments = PaymentNestedSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Borrowing
        fields = (
            'id',
            'borrow_date',
            'expected_return_date',
            'actual_return_date',
            'book',
            'user',
            'payments',
            'is_overdue',
        )
        read_only_fields = ('id',)


class BorrowingReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ('id', 'actual_return_date')
        read_only_fields = ('id', 'actual_return_date')
'''
write_file('borrowings/serializers.py', borrowings_serializers)

borrowings_views = '''
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from payments.models import Payment
from .models import Borrowing
from .serializers import (
    BorrowingSerializer,
    BorrowingCreateSerializer,
    BorrowingListSerializer,
    BorrowingDetailSerializer,
    BorrowingReturnSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary='List all borrowings',
        description='Get a list of borrowings. Admins see all, users see only their own.',
        parameters=[
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by active borrowings (no actual return date)',
            ),
            OpenApiParameter(
                name='user_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Admin only: Filter by user ID',
            ),
            OpenApiParameter(
                name='actual_return_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter by actual return date',
            ),
        ],
        tags=['Borrowings'],
    ),
    create=extend_schema(
        summary='Create a new borrowing',
        description='Borrow a book from the library',
        tags=['Borrowings'],
    ),
    retrieve=extend_schema(
        summary='Get borrowing details',
        description='Get detailed information about a specific borrowing',
        tags=['Borrowings'],
    ),
    return_book=extend_schema(
        summary='Return a borrowed book',
        description='Mark a borrowing as returned. Creates fine payment if overdue.',
        tags=['Borrowings'],
    ),
)
class BorrowingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BorrowingCreateSerializer
        if self.action == 'list':
            return BorrowingListSerializer
        if self.action == 'return_book':
            return BorrowingReturnSerializer
        return BorrowingDetailSerializer
    
    def get_queryset(self):
        queryset = Borrowing.objects.select_related('book', 'user').prefetch_related('payments')
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        else:
            user_id = self.request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() in ('true', '1', 'yes'):
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() in ('false', '0', 'no'):
                queryset = queryset.filter(actual_return_date__isnull=False)
        
        actual_return_date = self.request.query_params.get('actual_return_date')
        if actual_return_date:
            queryset = queryset.filter(actual_return_date=actual_return_date)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        # Check if user has pending payments
        pending_payments = Payment.objects.filter(
            borrowing__user=request.user,
            status=Payment.Status.PENDING,
        ).exists()
        
        if pending_payments:
            return Response(
                {'error': 'You have pending payments. Please pay them before borrowing new books.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().create(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], url_path='return')
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        
        if borrowing.actual_return_date is not None:
            return Response(
                {'error': 'This book has already been returned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user owns this borrowing
        if not request.user.is_staff and borrowing.user != request.user:
            return Response(
                {'error': 'You can only return your own borrowings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        borrowing.return_book()
        
        # Create fine payment if overdue
        if borrowing.is_overdue:
            fine_amount = borrowing.calculate_fine_amount()
            domain_url = 'http://localhost:8000'
            
            Payment.objects.create(
                borrowing=borrowing,
                type=Payment.Type.FINE,
                status=Payment.Status.PENDING,
                money_to_pay=fine_amount,
                session_url=f"{domain_url}/api/v1/payments/success/?session_id=fine_{borrowing.id}",
                session_id=f"fine_{borrowing.id}",
            )
            
            return Response({
                'message': f'Book returned successfully. You have an overdue fine of ${fine_amount}',
                'fine_amount': str(fine_amount),
                'overdue_days': borrowing.overdue_days,
            })
        
        serializer = BorrowingDetailSerializer(borrowing)
        return Response({
            'message': 'Book returned successfully',
            'borrowing': serializer.data,
        })
'''
write_file('borrowings/views.py', borrowings_views)

borrowings_urls = '''
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import BorrowingViewSet

router = DefaultRouter()
router.register('', BorrowingViewSet, basename='borrowing')

urlpatterns = [
    path('', include(router.urls)),
]
'''
write_file('borrowings/urls.py', borrowings_urls)

borrowings_admin = '''
from django.contrib import admin
from .models import Borrowing


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('id', 'book', 'user', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_active')
    list_filter = ('borrow_date', 'expected_return_date', 'actual_return_date')
    search_fields = ('book__title', 'user__email')
    ordering = ('-borrow_date',)
    date_hierarchy = 'borrow_date'
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = 'Active'
'''
write_file('borrowings/admin.py', borrowings_admin)

write_file('borrowings/__init__.py', '')
write_file('borrowings/apps.py', '''
from django.apps import AppConfig


class BorrowingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'borrowings'
''')

# manage.py
manage_content = '''#!/usr/bin/env python
import os
import sys


def main():
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
'''
write_file('manage.py', manage_content)

# requirements.txt
requirements_content = '''Django>=4.2,<5.0
djangorestframework>=3.14.0
djangorestframework-simplejwt>=5.3.0
drf-spectacular>=0.26.0
django-cors-headers>=4.0.0
django-filter>=23.0
stripe>=5.0.0
psycopg2-binary>=2.9.0
python-decouple>=3.8
gunicorn>=21.0.0
'''
write_file('requirements.txt', requirements_content)

# Dockerfile
dockerfile_content = '''FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "library_service.wsgi:application"]
'''
write_file('Dockerfile', dockerfile_content)

# docker-compose.yml
docker_compose_content = '''version: '3.8'

services:
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_DB: library_service
      POSTGRES_USER: library_user
      POSTGRES_PASSWORD: library_password
    ports:
      - "5432:5432"

  web:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             python manage.py runserver 0.0.0.0:8000"
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
      - SECRET_KEY=your-secret-key-change-in-production
      - DB_ENGINE=django.db.backends.postgresql
      - DB_NAME=library_service
      - DB_USER=library_user
      - DB_PASSWORD=library_password
      - DB_HOST=db
      - DB_PORT=5432
      - STRIPE_SECRET_KEY=sk_test_your_stripe_key
      - STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
      - DOMAIN_URL=http://localhost:8000
    depends_on:
      - db

volumes:
  postgres_data:
'''
write_file('docker-compose.yml', docker_compose_content)

# .env.example
env_example = '''DEBUG=True
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME=library_service
DB_USER=library_user
DB_PASSWORD=library_password
DB_HOST=localhost
DB_PORT=5432

STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

DOMAIN_URL=http://localhost:8000
'''
write_file('.env.example', env_example)

# README.md
readme_content = '''# Library Service API

API Library service for borrowing books written on DRF and Dockerized.

## Features

- JWT authentication
- Admin panel at `/admin/`
- API documentation at `/api/v1/doc/swagger/`
- Manage borrowings and payments
- Book borrowing and returning
- Payment processing after borrowing
- Fine payment for overdue borrowings
- Filtering for every endpoint

## Setup

### Local Development

1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (Linux/Mac) or `venv\\Scripts\\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure
6. Run migrations: `python manage.py migrate`
7. Create superuser: `python manage.py createsuperuser`
8. Run server: `python manage.py runserver`

### Docker

1. Copy `.env.example` to `.env` and configure
2. Run: `docker-compose up --build`

## API Endpoints

### Authentication
- `POST /api/v1/users/token/` - Get JWT tokens
- `POST /api/v1/users/token/refresh/` - Refresh access token
- `POST /api/v1/users/token/verify/` - Verify token

### Users
- `POST /api/v1/users/register/` - Register new user
- `GET/PUT/PATCH /api/v1/users/me/` - Get/Update current user

### Books
- `GET /api/v1/books/` - List all books
- `POST /api/v1/books/` - Create book (admin only)
- `GET /api/v1/books/{id}/` - Get book details
- `PUT/PATCH /api/v1/books/{id}/` - Update book (admin only)
- `DELETE /api/v1/books/{id}/` - Delete book (admin only)

### Borrowings
- `GET /api/v1/borrowings/` - List borrowings
- `POST /api/v1/borrowings/` - Create borrowing
- `GET /api/v1/borrowings/{id}/` - Get borrowing details
- `POST /api/v1/borrowings/{id}/return/` - Return book

### Payments
- `GET /api/v1/payments/` - List payments
- `GET /api/v1/payments/{id}/` - Get payment details
- `GET /api/v1/payments/success/` - Payment success callback
- `GET /api/v1/payments/cancel/` - Payment cancel callback

## Filtering

### Borrowings
- `?is_active=true/false` - Filter by active status
- `?user_id={id}` - Filter by user (admin only)
- `?actual_return_date={date}` - Filter by actual return date

### Payments
- `?status=PENDING/PAID/EXPIRED` - Filter by status
- `?type=PAYMENT/FINE` - Filter by type

### Books
- `?title={title}` - Filter by title
- `?author={author}` - Filter by author
- `?cover=HARD/SOFT` - Filter by cover type
'''
write_file('README.md', readme_content)

print("Library Service API project structure created successfully!")
print("\nProject structure:")
print("├── library_service/")
print("│   ├── __init__.py")
print("│   ├── settings.py")
print("│   ├── urls.py")
print("│   ├── wsgi.py")
print("│   └── asgi.py")
print("├── users/")
print("│   ├── __init__.py")
print("│   ├── apps.py")
print("│   ├── models.py")
print("│   ├── serializers.py")
print("│   ├── views.py")
print("│   ├── urls.py")
print("│   └── admin.py")
print("├── books/")
print("│   ├── __init__.py")
print("│   ├── apps.py")
print("│   ├── models.py")
print("│   ├── serializers.py")
print("│   ├── views.py")
print("│   ├── urls.py")
print("│   ├── permissions.py")
print("│   └── admin.py")
print("├── borrowings/")
print("│   ├── __init__.py")
print("│   ├── apps.py")
print("│   ├── models.py")
print("│   ├── serializers.py")
print("│   ├── views.py")
print("│   ├── urls.py")
print("│   └── admin.py")
print("├── payments/")
print("│   ├── __init__.py")
print("│   ├── apps.py")
print("│   ├── models.py")
print("│   ├── serializers.py")
print("│   ├── views.py")
print("│   ├── urls.py")
print("│   └── admin.py")
print("├── manage.py")
print("├── requirements.txt")
print("├── Dockerfile")
print("├── docker-compose.yml")
print("├── .env.example")
print("└── README.md")

print("\nTo run the project:")
print("1. pip install -r requirements.txt")
print("2. python manage.py migrate")
print("3. python manage.py createsuperuser")
print("4. python manage.py runserver")
print("\nAPI Documentation: http://localhost:8000/api/v1/doc/swagger/")
print("Admin Panel: http://localhost:8000/admin/")