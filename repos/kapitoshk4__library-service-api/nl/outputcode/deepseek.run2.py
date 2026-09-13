# manage.py
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library.settings')
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

# library/__init__.py
# (empty)

# library/settings.py
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-me')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

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
    'users',
    'books',
    'borrowings',
    'payments',
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

ROOT_URLCONF = 'library.urls'

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

WSGI_APPLICATION = 'library.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

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
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Library Service API',
    'DESCRIPTION': 'API for borrowing books and managing payments',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Fine multiplier for overdue days
FINE_MULTIPLIER = 2

# Stripe settings (optional, for real payment integration)
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', None)
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', None)

# library/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include([
        path('auth/', include('users.urls')),
        path('books/', include('books.urls')),
        path('borrowings/', include('borrowings.urls')),
        path('payments/', include('payments.urls')),
        path('schema/', SpectacularAPIView.as_view(), name='schema'),
        path('doc/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    ])),
]

# library/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library.settings')
application = get_wsgi_application()

# users/__init__.py
# (empty)

# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

admin.site.register(User, UserAdmin)

# users/serializers.py
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name')

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'first_name', 'last_name')

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user

# users/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import UserSerializer, UserRegistrationSerializer
from .models import User

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

# users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, MeView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', MeView.as_view(), name='me'),
]

# books/__init__.py
# (empty)

# books/models.py
from django.db import models

class Book(models.Model):
    COVER_HARD = 'HARD'
    COVER_SOFT = 'SOFT'
    COVER_CHOICES = [
        (COVER_HARD, 'Hard'),
        (COVER_SOFT, 'Soft'),
    ]

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=10, choices=COVER_CHOICES, default=COVER_HARD)
    inventory = models.PositiveIntegerField(default=1)
    daily_fee = models.DecimalField(max_digits=7, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.author})"

# books/admin.py
from django.contrib import admin
from .models import Book

admin.site.register(Book)

# books/serializers.py
from rest_framework import serializers
from .models import Book

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'cover', 'inventory', 'daily_fee', 'is_active')
        read_only_fields = ('id',)

class BookListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'cover', 'inventory', 'daily_fee')

# books/filters.py
import django_filters
from .models import Book

class BookFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Book
        fields = ['title', 'author', 'cover', 'is_active']

# books/views.py
from rest_framework import viewsets, permissions, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Book
from .serializers import BookSerializer
from .filters import BookFilter

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.filter(is_active=True)
    serializer_class = BookSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = BookFilter
    search_fields = ['title', 'author']
    ordering_fields = ['title', 'author', 'daily_fee', 'inventory']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()

# books/urls.py
from rest_framework.routers import DefaultRouter
from .views import BookViewSet

router = DefaultRouter()
router.register(r'', BookViewSet, basename='book')
urlpatterns = router.urls

# borrowings/__init__.py
# (empty)

# borrowings/models.py
from django.db import models
from django.conf import settings
from books.models import Book
from decimal import Decimal

class Borrowing(models.Model):
    STATUS_BORROWED = 'BORROWED'
    STATUS_RETURNED = 'RETURNED'
    STATUS_CHOICES = [
        (STATUS_BORROWED, 'Borrowed'),
        (STATUS_RETURNED, 'Returned'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_BORROWED)
    fine_amount = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-borrow_date']

    def __str__(self):
        return f"{self.user.email} borrowed {self.book.title} on {self.borrow_date}"

# borrowings/admin.py
from django.contrib import admin
from .models import Borrowing

admin.site.register(Borrowing)

# borrowings/filters.py
import django_filters
from .models import Borrowing

class BorrowingFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='user__id')
    user_email = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    actual_return_date = django_filters.DateFromToRangeFilter()
    borrow_date = django_filters.DateFromToRangeFilter()
    expected_return_date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Borrowing
        fields = ['user', 'status', 'actual_return_date', 'borrow_date', 'expected_return_date']

# borrowings/serializers.py
from rest_framework import serializers
from .models import Borrowing
from books.models import Book
from django.utils import timezone

class BorrowingSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.filter(is_active=True))
    book_title = serializers.CharField(source='book.title', read_only=True)

    class Meta:
        model = Borrowing
        fields = ('id', 'user', 'book', 'book_title', 'borrow_date', 'expected_return_date',
                  'actual_return_date', 'status', 'fine_amount')
        read_only_fields = ('id', 'user', 'borrow_date', 'actual_return_date', 'status', 'fine_amount')

    def validate(self, attrs):
        book = attrs['book']
        if book.inventory <= 0:
            raise serializers.ValidationError("Book is out of stock")
        expected_return = attrs['expected_return_date']
        if expected_return <= timezone.now().date():
            raise serializers.ValidationError("Expected return date must be in the future")
        return attrs

class BorrowingReturnSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField(required=False)

# borrowings/views.py
from rest_framework import viewsets, permissions, status, decorators
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from .models import Borrowing
from .serializers import BorrowingSerializer, BorrowingReturnSerializer
from .filters import BorrowingFilter
from payments.models import Payment

class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filterset_class = BorrowingFilter

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Borrowing.objects.all()
        return Borrowing.objects.filter(user=user)

    @transaction.atomic
    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        book.inventory -= 1
        book.save()
        serializer.save(user=self.request.user)

    @decorators.action(detail=True, methods=['post'])
    @transaction.atomic
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.status != Borrowing.STATUS_BORROWED:
            return Response({'error': 'Book already returned'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = BorrowingReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actual_date = serializer.validated_data.get('actual_return_date', timezone.now().date())
        borrowing.actual_return_date = actual_date
        borrowing.status = Borrowing.STATUS_RETURNED

        # Calculate fine if overdue
        if actual_date > borrowing.expected_return_date:
            overdue_days = (actual_date - borrowing.expected_return_date).days
            fine = overdue_days * borrowing.book.daily_fee * settings.FINE_MULTIPLIER
            borrowing.fine_amount = fine
            # Create fine payment
            Payment.objects.create(
                user=borrowing.user,
                borrowing=borrowing,
                type=Payment.TYPE_FINE,
                money_to_pay=fine,
                status=Payment.STATUS_PENDING,
            )

        borrowing.save()
        # Increase inventory
        book = borrowing.book
        book.inventory += 1
        book.save()
        return Response(BorrowingSerializer(borrowing).data)

# borrowings/urls.py
from rest_framework.routers import DefaultRouter
from .views import BorrowingViewSet

router = DefaultRouter()
router.register(r'', BorrowingViewSet, basename='borrowing')
urlpatterns = router.urls

# payments/__init__.py
# (empty)

# payments/models.py
from django.db import models
from django.conf import settings
from borrowings.models import Borrowing

class Payment(models.Model):
    TYPE_PAYMENT = 'PAYMENT'
    TYPE_FINE = 'FINE'
    TYPE_CHOICES = [
        (TYPE_PAYMENT, 'Payment'),
        (TYPE_FINE, 'Fine'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_PAID = 'PAID'
    STATUS_EXPIRED = 'EXPIRED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_PAYMENT)
    money_to_pay = models.DecimalField(max_digits=7, decimal_places=2)
    session_url = models.URLField(max_length=500, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} #{self.id} - {self.status}"

# payments/admin.py
from django.contrib import admin
from .models import Payment

admin.site.register(Payment)

# payments/serializers.py
from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    borrowing_id = serializers.IntegerField(source='borrowing.id', read_only=True)

    class Meta:
        model = Payment
        fields = ('id', 'user', 'borrowing', 'borrowing_id', 'type', 'money_to_pay',
                  'session_url', 'session_id', 'status', 'created_at')
        read_only_fields = ('id', 'user', 'borrowing', 'type', 'money_to_pay',
                            'session_url', 'session_id', 'status', 'created_at')

class PaymentCreateSerializer(serializers.Serializer):
    borrowing_id = serializers.IntegerField()

# payments/views.py
from rest_framework import generics, permissions, status, filters as drf_filters
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from django.conf import settings as conf_settings
from django.shortcuts import get_object_or_404
from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer
from borrowings.models import Borrowing
from django.utils import timezone
import uuid
import stripe

class PaymentFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='user__id')
    type = django_filters.CharFilter()
    status = django_filters.CharFilter()
    class Meta:
        model = Payment
        fields = ['user', 'type', 'status']

class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['created_at', 'money_to_pay']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=user)

class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=user)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_payment_session(request):
    serializer = PaymentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    borrowing_id = serializer.validated_data['borrowing_id']
    borrowing = get_object_or_404(Borrowing, id=borrowing_id, user=request.user)
    if borrowing.status != Borrowing.STATUS_BORROWED:
        return Response({'error': 'Borrowing is not active'}, status=status.HTTP_400_BAD_REQUEST)

    # Calculate borrowing fee
    days = (borrowing.expected_return_date - borrowing.borrow_date).days
    if days <= 0:
        days = 1
    amount = days * borrowing.book.daily_fee

    # Check if there is already a pending PAYMENT for this borrowing
    existing = Payment.objects.filter(borrowing=borrowing, type=Payment.TYPE_PAYMENT, status=Payment.STATUS_PENDING).first()
    if existing:
        return Response(PaymentSerializer(existing).data, status=status.HTTP_200_OK)

    # Create payment
    payment = Payment.objects.create(
        user=request.user,
        borrowing=borrowing,
        type=Payment.TYPE_PAYMENT,
        money_to_pay=amount,
        status=Payment.STATUS_PENDING,
    )

    # If Stripe is configured, create checkout session
    if conf_settings.STRIPE_SECRET_KEY:
        stripe.api_key = conf_settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Borrowing fee for {borrowing.book.title}',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url='http://example.com/success',
                cancel_url='http://example.com/cancel',
                metadata={
                    'payment_id': payment.id,
                    'user_id': request.user.id,
                }
            )
            payment.session_url = session.url
            payment.session_id = session.id
            payment.save()
        except Exception as e:
            # Log error, but don't block creation
            pass

    return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    if conf_settings.STRIPE_WEBHOOK_SECRET and conf_settings.STRIPE_SECRET_KEY:
        stripe.api_key = conf_settings.STRIPE_SECRET_KEY
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, conf_settings.STRIPE_WEBHOOK_SECRET)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            payment_id = session['metadata'].get('payment_id')
            try:
                payment = Payment.objects.get(id=payment_id)
                payment.status = Payment.STATUS_PAID
                payment.save()
            except Payment.DoesNotExist:
                pass
    return Response(status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_payment(request, payment_id):
    """Simulate payment confirmation (for testing without Stripe)"""
    payment = get_object_or_404(Payment, id=payment_id)
    if payment.user != request.user and not request.user.is_staff:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    if payment.status != Payment.STATUS_PENDING:
        return Response({'error': 'Payment not in pending state'}, status=status.HTTP_400_BAD_REQUEST)
    payment.status = Payment.STATUS_PAID
    payment.save()
    return Response(PaymentSerializer(payment).data)

# payments/urls.py
from django.urls import path
from .views import PaymentListView, PaymentDetailView, create_payment_session, stripe_webhook, confirm_payment

urlpatterns = [
    path('', PaymentListView.as_view(), name='payment-list'),
    path('<int:id>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('create-session/', create_payment_session, name='create-payment-session'),
    path('webhook/', stripe_webhook, name='stripe-webhook'),
    path('<int:payment_id>/confirm/', confirm_payment, name='confirm-payment'),
]

# requirements.txt (for reference, not part of code)
# Django>=4.2,<5.0
# djangorestframework>=3.14
# djangorestframework-simplejwt
# django-filter
# drf-spectacular
# stripe (optional)