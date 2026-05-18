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

# filename: library_service/settings.py
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-please-change')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_filters',
    # Local
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
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ.get('DB_NAME', 'library_db'),
        'USER': os.environ.get('DB_USER', 'library_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'library_password'),
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', '5432'),
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

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# SimpleJWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Library Service API',
    'DESCRIPTION': 'API for borrowing books with payments and fines',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Borrowing constants
BORROWING_FEE = 5.00
FINE_PER_DAY = 1.00

# filename: library_service/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('library.urls')),
    path('api/v1/doc/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# filename: library_service/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_wsgi_application()

# filename: library/__init__.py

# filename: library/models.py
from decimal import Decimal
from datetime import date
from django.db import models
from django.conf import settings
from django.utils import timezone


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True)
    description = models.TextField(blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_added']

    def __str__(self):
        return self.title


class Borrowing(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='borrowings'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='borrowings'
    )
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-borrow_date']

    def __str__(self):
        return f'{self.user.username} borrowed {self.book.title}'

    @property
    def is_overdue(self):
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return date.today() > self.expected_return_date


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        FEE = 'FEE', 'Borrowing Fee'
        FINE = 'FINE', 'Fine'

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'

    borrowing = models.ForeignKey(
        Borrowing,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    payment_type = models.CharField(max_length=4, choices=PaymentType.choices)
    status = models.CharField(
        max_length=7,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f'{self.payment_type} - {self.amount} ({self.status})'

# filename: library/serializers.py
from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from django.conf import settings

from .models import Book, Borrowing, Payment


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = ('date_added',)


class BorrowingSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Borrowing
        fields = [
            'id', 'user', 'book', 'borrow_date',
            'expected_return_date', 'actual_return_date', 'is_overdue'
        ]
        read_only_fields = ('borrow_date', 'user')

    def validate(self, data):
        if 'actual_return_date' in data and data['actual_return_date'] < data.get('borrow_date', timezone.now().date()):
            raise serializers.ValidationError("Return date cannot be before borrow date.")
        return data


class BorrowingCreateSerializer(BorrowingSerializer):
    class Meta(BorrowingSerializer.Meta):
        pass

    def create(self, validated_data):
        user = self.context['request'].user
        borrowing = Borrowing.objects.create(user=user, **validated_data)
        # Auto-create pending fee payment
        Payment.objects.create(
            borrowing=borrowing,
            amount=Decimal(settings.BORROWING_FEE),
            payment_type=Payment.PaymentType.FEE,
            status=Payment.PaymentStatus.PENDING
        )
        return borrowing


class PaymentSerializer(serializers.ModelSerializer):
    borrowing_id = serializers.IntegerField(source='borrowing.id', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'borrowing_id', 'amount', 'payment_date', 'payment_type', 'status']
        read_only_fields = ('payment_date',)


# filename: library/filters.py
import django_filters
from .models import Borrowing


class BorrowingFilter(django_filters.FilterSet):
    actual_return_date = django_filters.DateFilter(
        field_name='actual_return_date',
        lookup_expr='exact',
        help_text='Filter by exact actual return date'
    )
    actual_return_date_range = django_filters.DateFromToRangeFilter(
        field_name='actual_return_date',
        help_text='Filter by date range (e.g. ?actual_return_date_range_after=2024-01-01&actual_return_date_range_before=2024-12-31)'
    )
    user = django_filters.NumberFilter(field_name='user__id')
    user_username = django_filters.CharFilter(
        field_name='user__username',
        lookup_expr='icontains',
        help_text='Filter by username (case insensitive contains)'
    )

    class Meta:
        model = Borrowing
        fields = {
            'expected_return_date': ['exact'],
            'borrow_date': ['exact'],
        }

# filename: library/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingSerializer,
    BorrowingCreateSerializer,
    PaymentSerializer
)
from .filters import BorrowingFilter


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff


class IsOwnerBorrowingOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # For payments, ownership is through borrowing.user
        return obj.borrowing.user == request.user or request.user.is_staff


@extend_schema_view(
    list=extend_schema(description='List all books'),
    retrieve=extend_schema(description='Retrieve a book'),
    create=extend_schema(description='Create a new book (admin only)'),
    update=extend_schema(description='Update a book (admin only)'),
    partial_update=extend_schema(description='Partially update a book (admin only)'),
    destroy=extend_schema(description='Delete a book (admin only)'),
)
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAdminOrReadOnly]


@extend_schema_view(
    list=extend_schema(description='List user borrowings (admin sees all)'),
    retrieve=extend_schema(description='Retrieve a borrowing'),
    create=extend_schema(description='Create a new borrowing (with fee payment)'),
    update=extend_schema(description='Update a borrowing (owner or admin)'),
    partial_update=extend_schema(description='Partially update a borrowing'),
    destroy=extend_schema(description='Delete a borrowing'),
)
class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filterset_class = BorrowingFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return BorrowingCreateSerializer
        return BorrowingSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Borrowing.objects.all()
        return Borrowing.objects.filter(user=user)

    @extend_schema(
        description='Return a borrowed book. Sets actual return date and creates fine if overdue.',
        request=None,
        responses={200: BorrowingSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOrAdmin])
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.actual_return_date is not None:
            return Response(
                {'detail': 'Book has already been returned.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        borrowing.actual_return_date = timezone.now().date()
        borrowing.save()

        # Check and create fine
        if borrowing.actual_return_date > borrowing.expected_return_date:
            overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
            fine_amount = Decimal(overdue_days * settings.FINE_PER_DAY)
            Payment.objects.create(
                borrowing=borrowing,
                amount=fine_amount,
                payment_type=Payment.PaymentType.FINE,
                status=Payment.PaymentStatus.PENDING
            )

        serializer = self.get_serializer(borrowing)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(description='List payments (user sees their own, admin sees all)'),
    retrieve=extend_schema(description='Retrieve a payment'),
)
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerBorrowingOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(borrowing__user=user)

# filename: library/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import BookViewSet, BorrowingViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')
router.register(r'borrowings', BorrowingViewSet, basename='borrowing')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]

# filename: library/admin.py
from django.contrib import admin
from .models import Book, Borrowing, Payment


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'date_added')
    search_fields = ('title', 'author', 'isbn')


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_overdue')
    list_filter = ('borrow_date', 'expected_return_date', 'actual_return_date')
    search_fields = ('user__username', 'book__title')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'borrowing', 'amount', 'payment_date', 'payment_type', 'status')
    list_filter = ('payment_type', 'status', 'payment_date')
    search_fields = ('borrowing__user__username',)

# filename: requirements.txt
Django>=4.2,<5
djangorestframework>=3.14
djangorestframework-simplejwt>=5.3
drf-spectacular>=0.26
django-filter>=23.2
psycopg2-binary>=2.9
gunicorn>=20.1

# filename: Dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "library_service.wsgi:application", "--bind", "0.0.0.0:8000"]

# filename: docker-compose.yml
version: "3.9"

services:
  web:
    build: .
    command: >
      sh -c "python manage.py migrate &&
             gunicorn library_service.wsgi:application --bind 0.0.0.0:8000"
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_DB: library_db
      POSTGRES_USER: library_user
      POSTGRES_PASSWORD: library_password

volumes:
  postgres_data:

# filename: .env.example
DJANGO_SECRET_KEY=change-me-to-a-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*
DB_ENGINE=django.db.backends.postgresql
DB_NAME=library_db
DB_USER=library_user
DB_PASSWORD=library_password
DB_HOST=db
DB_PORT=5432