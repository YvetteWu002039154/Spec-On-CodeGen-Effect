# ========== project/requirements.txt ==========
Django>=4.2,<5.0
djangorestframework>=3.14.0
djangorestframework-simplejwt>=5.2.2
drf-yasg>=1.21.5
django-filter>=23.2
psycopg2-binary>=2.9.6

# ========== project/manage.py ==========
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

# ========== project/library_service/settings.py ==========
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'change-me-in-production')

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
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

# ========== project/library_service/urls.py ==========
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Library API",
        default_version='v1',
        description="API for borrowing books, managing payments, and fines",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('library.urls')),
    re_path(r'^api/v1/doc/swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/v1/doc/swagger/',
         schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
]

# ========== project/library_service/wsgi.py ==========
"""
WSGI config for library_service project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_wsgi_application()

# ========== project/library/__init__.py ==========
default_app_config = 'library.apps.LibraryConfig'

# ========== project/library/apps.py ==========
from django.apps import AppConfig

class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'library'

# ========== project/library/models.py ==========
from django.db import models
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

User = get_user_model()

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    inventory = models.PositiveIntegerField(default=0)
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Rental fee per day")
    fine_per_day = models.DecimalField(max_digits=10, decimal_places=2, help_text="Fine per day if overdue")

    def __str__(self):
        return self.title

class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} borrowed {self.book} on {self.borrow_date}"

    def save(self, *args, **kwargs):
        if not self.expected_return_date:
            self.expected_return_date = self.borrow_date + timedelta(days=7)  # default 7 days
        super().save(*args, **kwargs)

class Payment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
    )
    TYPE_CHOICES = (
        ('BORROWING_FEE', 'Borrowing Fee'),
        ('FINE', 'Fine'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    session_id = models.CharField(max_length=255, blank=True, null=True)  # for external payment integration

    def __str__(self):
        return f"{self.payment_type} - {self.amount} - {self.status}"

# ========== project/library/admin.py ==========
from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'inventory', 'daily_fee', 'fine_per_day')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_active')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'borrowing', 'amount', 'status', 'payment_type', 'payment_date')

# ========== project/library/serializers.py ==========
from rest_framework import serializers
from .models import Book, Borrowing, Payment
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

User = get_user_model()

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class BorrowingSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Borrowing
        fields = ['id', 'borrow_date', 'expected_return_date', 'actual_return_date',
                  'book', 'book_title', 'user', 'user_email', 'is_active']
        read_only_fields = ['borrow_date', 'is_active', 'user']

    def validate(self, data):
        if self.instance is None:  # creation
            book = data['book']
            if book.inventory <= 0:
                raise serializers.ValidationError("Book is out of stock.")
            data['user'] = self.context['request'].user
        return data

    def create(self, validated_data):
        book = validated_data['book']
        user = validated_data['user']
        duration = (validated_data['expected_return_date'] - date.today()).days
        if duration <= 0:
            raise serializers.ValidationError("Expected return date must be in the future.")
        with transaction.atomic():
            book.inventory -= 1
            book.save()
            borrowing = Borrowing.objects.create(**validated_data, borrow_date=date.today())
            fee_amount = book.daily_fee * duration
            Payment.objects.create(
                user=user,
                borrowing=borrowing,
                amount=fee_amount,
                payment_type='BORROWING_FEE',
                status='PENDING'
            )
            return borrowing

from django.db import transaction
class BorrowingReturnSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField()

    def validate_actual_return_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Return date cannot be in the future.")
        return value

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['user', 'amount', 'payment_type', 'borrowing', 'session_id', 'payment_date']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

# ========== project/library/filters.py ==========
import django_filters
from .models import Borrowing, Payment, Book

class BorrowingFilter(django_filters.FilterSet):
    actual_return_date = django_filters.DateFilter()
    actual_return_date__gte = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='gte')
    actual_return_date__lte = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='lte')
    user = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    user_id = django_filters.NumberFilter(field_name='user__id')
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = Borrowing
        fields = ['actual_return_date', 'user', 'is_active', 'user_id']

class PaymentFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=Payment.STATUS_CHOICES)
    payment_type = django_filters.ChoiceFilter(choices=Payment.TYPE_CHOICES)

    class Meta:
        model = Payment
        fields = ['user', 'status', 'payment_type']

class BookFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Book
        fields = ['title', 'author']

# ========== project/library/views.py ==========
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from datetime import date
from .models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingSerializer,
    BorrowingReturnSerializer,
    PaymentSerializer,
    UserSerializer,
)
from .filters import BorrowingFilter, PaymentFilter, BookFilter
from django.contrib.auth import get_user_model

User = get_user_model()

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_class = BookFilter
    search_fields = ['title', 'author']
    ordering_fields = ['title', 'author', 'daily_fee']

class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = BorrowingFilter
    search_fields = ['user__email', 'book__title']
    ordering_fields = ['borrow_date', 'expected_return_date', 'actual_return_date']

    def get_queryset(self):
        if self.request.user.is_staff:
            return Borrowing.objects.all()
        return Borrowing.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], serializer_class=BorrowingReturnSerializer)
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.actual_return_date is not None:
            return Response({"detail": "Book already returned."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actual_return_date = serializer.validated_data['actual_return_date']
        with transaction.atomic():
            borrowing.actual_return_date = actual_return_date
            borrowing.is_active = False
            borrowing.save()
            borrowing.book.inventory += 1
            borrowing.book.save()
            if actual_return_date > borrowing.expected_return_date:
                days_overdue = (actual_return_date - borrowing.expected_return_date).days
                fine_amount = days_overdue * borrowing.book.fine_per_day
                Payment.objects.create(
                    user=borrowing.user,
                    borrowing=borrowing,
                    amount=fine_amount,
                    payment_type='FINE',
                    status='PENDING'
                )
        return Response({"detail": "Book returned successfully."})

    @action(detail=False, methods=['get'], url_path='my')
    def my_borrowings(self, request):
        borrowings = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(borrowings, many=True)
        return Response(serializer.data)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = PaymentFilter
    search_fields = ['user__email']
    ordering_fields = ['payment_date', 'amount', 'status']

    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        payment = self.get_object()
        if payment.status == 'PAID':
            return Response({"detail": "Payment already completed."}, status=status.HTTP_400_BAD_REQUEST)
        # Here you would integrate with payment gateway and set session_id
        # For simplicity, we mark as paid directly
        payment.status = 'PAID'
        payment.payment_date = timezone.now()
        payment.save()
        return Response({"detail": "Payment successful."})

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

# ========== project/library/urls.py ==========
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, BorrowingViewSet, PaymentViewSet, UserViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'borrowings', BorrowingViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]

# ========== project/library/migrations/0001_initial.py ==========
# This file is automatically generated by Django, but included as a placeholder.
# Run `python manage.py makemigrations library` to generate the actual migration.
# Minimal migration needed for SQLite:
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency('auth.user'),  # depend on the user model
    ]
    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('author', models.CharField(max_length=255)),
                ('inventory', models.PositiveIntegerField(default=0)),
                ('daily_fee', models.DecimalField(max_digits=10, decimal_places=2, help_text='Rental fee per day')),
                ('fine_per_day', models.DecimalField(max_digits=10, decimal_places=2, help_text='Fine per day if overdue')),
            ],
        ),
        migrations.CreateModel(
            name='Borrowing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('borrow_date', models.DateField(auto_now_add=True)),
                ('expected_return_date', models.DateField()),
                ('actual_return_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='borrowings', to='library.Book')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='borrowings', to='auth.user')),
            ],
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('payment_date', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid')], default='PENDING', max_length=20)),
                ('payment_type', models.CharField(choices=[('BORROWING_FEE', 'Borrowing Fee'), ('FINE', 'Fine')], max_length=20)),
                ('session_id', models.CharField(blank=True, max_length=255, null=True)),
                ('borrowing', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='library.Borrowing')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='auth.user')),
            ],
        ),
    ]