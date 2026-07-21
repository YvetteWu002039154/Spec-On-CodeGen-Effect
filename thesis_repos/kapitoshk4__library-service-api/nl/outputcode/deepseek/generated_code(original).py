# File: api/models.py
from django.db import models
from django.conf import settings
from decimal import Decimal
from datetime import date

class Book(models.Model):
    COVER_CHOICES = (
        ('HARD', 'Hardcover'),
        ('SOFT', 'Softcover'),
    )
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=4, choices=COVER_CHOICES, default='SOFT')
    inventory = models.PositiveIntegerField(default=1)
    daily_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    fine_per_day = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.title} ({self.author})"

    def available_copies(self):
        active_borrowings = self.borrowings.filter(actual_return_date__isnull=True).count()
        return self.inventory - active_borrowings

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
        return f"{self.book.title} borrowed by {self.user.username} on {self.borrow_date}"

    @property
    def is_active(self):
        return self.actual_return_date is None

    @property
    def is_overdue(self):
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return date.today() > self.expected_return_date

    def overdue_days(self):
        if self.actual_return_date:
            return (self.actual_return_date - self.expected_return_date).days
        if self.is_overdue:
            return (date.today() - self.expected_return_date).days
        return 0

class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('BORROWING_FEE', 'Borrowing Fee'),
        ('FINE', 'Fine'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
    )
    borrowing = models.ForeignKey(
        Borrowing,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=15, choices=PAYMENT_TYPE_CHOICES)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"{self.payment_type} payment for borrowing #{self.borrowing.id} - {self.status}"


# File: api/admin.py
from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'cover', 'inventory', 'daily_fee', 'fine_per_day')
    list_filter = ('cover',)
    search_fields = ('title', 'author')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_active')
    list_filter = ('actual_return_date', 'user')
    search_fields = ('user__username', 'book__title')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'borrowing', 'amount', 'payment_type', 'payment_date', 'status')
    list_filter = ('payment_type', 'status', 'payment_date')


# File: api/filters.py
import django_filters
from .models import Borrowing

class BorrowingFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='user_id', lookup_expr='exact')
    actual_return_date = django_filters.DateFilter(field_name='actual_return_date')

    class Meta:
        model = Borrowing
        fields = ['user', 'actual_return_date']


# File: api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Book, Borrowing, Payment
from datetime import date

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class BookSerializer(serializers.ModelSerializer):
    available_copies = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = ('id',)

    def get_available_copies(self, obj):
        return obj.available_copies()

class BorrowingListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    book = BookSerializer(read_only=True)
    is_active = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = '__all__'
        read_only_fields = ('id', 'user', 'book', 'borrow_date')

    def get_is_active(self, obj):
        return obj.is_active

    def get_is_overdue(self, obj):
        return obj.is_overdue

class BorrowingCreateSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Borrowing
        fields = ('book', 'expected_return_date', 'user')
        extra_kwargs = {'expected_return_date': {'required': True}}

    def validate(self, data):
        book = data['book']
        if book.available_copies() <= 0:
            raise serializers.ValidationError("No available copies of this book.")
        if data['expected_return_date'] <= date.today():
            raise serializers.ValidationError("Expected return date must be in the future.")
        return data

class BorrowingReturnSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField(default=date.today())

    def validate_actual_return_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Return date cannot be in the future.")
        return value

class PaymentSerializer(serializers.ModelSerializer):
    borrowing = serializers.PrimaryKeyRelatedField(queryset=Borrowing.objects.all())

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('id', 'payment_date', 'status')

class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('status',)


# File: api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from .views import BookViewSet, BorrowingViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'borrowings', BorrowingViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('doc/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('doc/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('', include(router.urls)),
]


# File: api/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingListSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
    PaymentSerializer,
    PaymentStatusSerializer,
)
from .filters import BorrowingFilter
from datetime import date

@extend_schema_view(
    list=extend_schema(description='List all books'),
    retrieve=extend_schema(description='Retrieve a book'),
    create=extend_schema(description='Add a new book (admin only)'),
    update=extend_schema(description='Update a book (admin only)'),
    partial_update=extend_schema(description='Partially update a book (admin only)'),
    destroy=extend_schema(description='Delete a book (admin only)'),
)
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['title', 'author', 'cover']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()

@extend_schema_view(
    list=extend_schema(description='List borrowings (filterable by user and actual_return_date)'),
    retrieve=extend_schema(description='Retrieve a borrowing'),
    create=extend_schema(description='Borrow a book'),
    return_book=extend_schema(description='Return a borrowed book'),
)
class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BorrowingFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return BorrowingCreateSerializer
        if self.action == 'return_book':
            return BorrowingReturnSerializer
        return BorrowingListSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Borrowing.objects.all()
        return Borrowing.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if not borrowing.is_active:
            return Response({"detail": "This borrowing has already been returned."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actual_return_date = serializer.validated_data['actual_return_date']
        borrowing.actual_return_date = actual_return_date
        borrowing.save()

        # Create fine payment if overdue
        if borrowing.is_overdue:
            fine_amount = borrowing.book.fine_per_day * borrowing.overdue_days()
            Payment.objects.create(
                borrowing=borrowing,
                amount=fine_amount,
                payment_type='FINE',
                status='PENDING'
            )

        return Response(BorrowingListSerializer(borrowing).data)

@extend_schema_view(
    list=extend_schema(description='List all payments (admin gets all, user gets own)'),
    retrieve=extend_schema(description='Retrieve a payment'),
    create=extend_schema(description='Create a payment for a borrowing'),
    update=extend_schema(description='Update payment status (admin only)'),
    partial_update=extend_schema(description='Partially update payment status (admin only)'),
)
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['payment_type', 'status', 'borrowing__user']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return PaymentStatusSerializer
        return PaymentSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(borrowing__user=self.request.user)

    def get_permissions(self):
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        borrowing = serializer.validated_data['borrowing']
        # Ensure the borrowing belongs to the current user
        if borrowing.user != self.request.user and not self.request.user.is_staff:
            raise PermissionError("You can only create payments for your own borrowings.")
        serializer.save()


# File: library_service/settings.py
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-&%#@!fake-key-change-in-production'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_filters',
    # Local
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
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Library Service API',
    'DESCRIPTION': 'API for borrowing books with payment and fine management',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}


# File: library_service/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
]
