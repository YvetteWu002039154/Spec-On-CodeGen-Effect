# requirements.txt
Django==4.2
djangorestframework==3.14
djangorestframework-simplejwt==5.2
drf-spectacular==0.26
django-filter==23.2

# manage.py
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

# library_service/__init__.py
# (empty)

# library_service/settings.py
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-in-production'

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
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Library Service API',
    'DESCRIPTION': 'API for managing library borrowings and payments',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# library_service/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('library.urls')),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
]

# library_service/wsgi.py
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_wsgi_application()

# library/__init__.py
# (empty)

# library/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True)
    publication_year = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    borrowing_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return self.title

class Borrowing(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('RETURNED', 'Returned'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateTimeField()
    actual_return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')

    def __str__(self):
        return f"{self.user} borrowed {self.book.title}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Create a borrowing fee payment automatically
            Payment.objects.create(
                borrowing=self,
                amount=self.book.borrowing_fee,
                payment_type='BORROWING_FEE',
                due_date=self.borrow_date + timezone.timedelta(minutes=1)
            )

class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('BORROWING_FEE', 'Borrowing Fee'),
        ('FINE', 'Fine'),
    ]
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    payment_type = models.CharField(max_length=15, choices=PAYMENT_TYPE_CHOICES)
    due_date = models.DateTimeField()
    paid_date = models.DateTimeField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.payment_type} {self.amount} for {self.borrowing}"

# library/admin.py
from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'borrowing_fee', 'is_active')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'status')
    list_filter = ('status', 'actual_return_date')
    search_fields = ('user__username', 'book__title')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('borrowing', 'amount', 'payment_type', 'due_date', 'paid_date', 'is_paid')
    list_filter = ('payment_type', 'is_paid')

# library/serializers.py
from rest_framework import serializers
from .models import Book, Borrowing, Payment
from django.utils import timezone

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('is_paid', 'paid_date')

class BorrowingSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    user_name = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Borrowing
        fields = ['id', 'user', 'user_name', 'book', 'borrow_date', 'expected_return_date',
                  'actual_return_date', 'status', 'payments']
        read_only_fields = ('borrow_date', 'actual_return_date', 'status', 'payments')

    def validate(self, data):
        if self.instance is None:  # creation
            book = data.get('book')
            if not book.is_active:
                raise serializers.ValidationError("This book is currently unavailable.")
            # Prevent borrowing a book already actively borrowed
            if Borrowing.objects.filter(book=book, status='ACTIVE').exists():
                raise serializers.ValidationError("This book is already borrowed.")
        return data

class ReturnBookSerializer(serializers.Serializer):
    actual_return_date = serializers.DateTimeField(default=timezone.now)

    def update(self, instance, validated_data):
        actual_return_date = validated_data.get('actual_return_date', timezone.now())
        instance.actual_return_date = actual_return_date
        instance.status = 'RETURNED'
        instance.save()

        # Calculate fine if overdue
        if actual_return_date > instance.expected_return_date:
            days_overdue = (actual_return_date - instance.expected_return_date).days + 1
            fine_amount = days_overdue * instance.book.borrowing_fee  # using borrowing_fee as daily fine for simplicity
            Payment.objects.create(
                borrowing=instance,
                amount=fine_amount,
                payment_type='FINE',
                due_date=actual_return_date + timezone.timedelta(days=1),
                is_paid=False
            )
        return instance

class PaymentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['paid_date']

    def update(self, instance, validated_data):
        instance.paid_date = validated_data.get('paid_date', timezone.now())
        instance.is_paid = True
        instance.save()
        return instance

# library/filters.py
import django_filters
from .models import Borrowing

class BorrowingFilter(django_filters.FilterSet):
    actual_return_date_from = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='gte')
    actual_return_date_to = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='lte')
    user = django_filters.NumberFilter(field_name='user_id')

    class Meta:
        model = Borrowing
        fields = {
            'expected_return_date': ['exact', 'gte', 'lte'],
            'status': ['exact'],
            'book': ['exact'],
        }

# library/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer, BorrowingSerializer, ReturnBookSerializer,
    PaymentSerializer, PaymentUpdateSerializer
)
from .filters import BorrowingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['title', 'author', 'isbn', 'is_active']

class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all().select_related('user', 'book').prefetch_related('payments')
    serializer_class = BorrowingSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = BorrowingFilter

    def get_queryset(self):
        # Regular users see only their own borrowings, admins see all
        if self.request.user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.status != 'ACTIVE':
            return Response({'detail': 'Book already returned.'}, status=status.HTTP_400_BAD_REQUEST)
        if borrowing.user != request.user and not request.user.is_staff:
            return Response({'detail': 'You do not have permission to return this book.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ReturnBookSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(borrowing, serializer.validated_data)
        borrowing.refresh_from_db()
        return Response(BorrowingSerializer(borrowing).data)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related('borrowing__user', 'borrowing__book')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(borrowing__user=self.request.user)

    @action(detail=True, methods=['patch'])
    def pay(self, request, pk=None):
        payment = self.get_object()
        if payment.is_paid:
            return Response({'detail': 'Payment already completed.'}, status=status.HTTP_400_BAD_REQUEST)
        if payment.borrowing.user != request.user and not request.user.is_staff:
            return Response({'detail': 'You do not have permission to pay this.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = PaymentUpdateSerializer(payment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PaymentSerializer(payment).data)

# library/urls.py
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