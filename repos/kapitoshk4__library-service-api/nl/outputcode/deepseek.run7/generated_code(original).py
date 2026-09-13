### FILE: requirements.txt
```
Django==4.2
djangorestframework==3.14.0
djangorestframework-simplejwt==5.2.2
drf-yasg==1.21.7
django-filter==23.2
```

### FILE: manage.py
```python
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
```

### FILE: library_service/settings.py
```python
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-this-is-a-secret-key-for-dev-only'

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
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
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
    'SLIDING_TOKEN_LIFETIME': timedelta(hours=2),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
        }
    },
    'USE_SESSION_AUTH': False,
}

# Loan constants
LOAN_DAYS = 14
FINE_PER_DAY = 1.00
```

### FILE: library_service/urls.py
```python
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('library.urls')),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

### FILE: library/__init__.py
```python
```

### FILE: library/models.py
```python
from django.db import models
from django.conf import settings
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    borrowing_fee = models.DecimalField(max_digits=6, decimal_places=2, default=2.00)

    def __str__(self):
        return self.title

    def is_available(self):
        return self.available_copies > 0


class Borrowing(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='borrowings')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrowings')
    borrow_date = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateTimeField()
    actual_return_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-borrow_date']

    def save(self, *args, **kwargs):
        if not self.pk and not self.expected_return_date:
            self.expected_return_date = self.borrow_date + timedelta(days=settings.LOAN_DAYS)
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.actual_return_date:
            return self.actual_return_date > self.expected_return_date
        return timezone.now() > self.expected_return_date


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        BORROWING_FEE = 'borrowing_fee', 'Borrowing Fee'
        FINE = 'fine', 'Fine'

    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'

    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    def __str__(self):
        return f"{self.payment_type} - {self.amount} - {self.status}"
```

### FILE: library/serializers.py
```python
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import Book, Borrowing, Payment

User = get_user_model()


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'isbn', 'total_copies', 'available_copies', 'borrowing_fee']
        read_only_fields = ['id', 'available_copies']


class BorrowingSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_isbn = serializers.CharField(source='book.isbn', read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = ['id', 'user', 'user_email', 'book', 'book_title', 'book_isbn',
                  'borrow_date', 'expected_return_date', 'actual_return_date', 'status']
        read_only_fields = ['id', 'borrow_date', 'user']

    def get_status(self, obj):
        if obj.actual_return_date:
            return 'returned'
        if obj.is_overdue:
            return 'overdue'
        return 'borrowed'


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ['book', 'expected_return_date']

    def validate_book(self, book):
        if not book.is_available():
            raise serializers.ValidationError("This book is not available for borrowing.")
        return book

    def create(self, validated_data):
        user = self.context['request'].user
        book = validated_data['book']
        expected_return_date = validated_data.get('expected_return_date', None)

        if not expected_return_date:
            expected_return_date = timezone.now() + timezone.timedelta(days=settings.LOAN_DAYS)

        # Create borrowing and decrement available copies inside transaction
        borrowing = Borrowing.objects.create(
            user=user,
            book=book,
            expected_return_date=expected_return_date
        )
        book.available_copies -= 1
        book.save()

        # Create pending borrowing fee payment
        Payment.objects.create(
            borrowing=borrowing,
            payment_type=Payment.PaymentType.BORROWING_FEE,
            amount=book.borrowing_fee,
            status=Payment.PaymentStatus.PENDING
        )
        return borrowing


class ReturnBookSerializer(serializers.Serializer):
    # No fields needed, just set actual_return_date to now
    pass


class PaymentSerializer(serializers.ModelSerializer):
    borrowing_id = serializers.IntegerField(source='borrowing.id', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'borrowing_id', 'payment_type', 'amount', 'payment_date', 'status']
        read_only_fields = ['id', 'borrowing_id', 'payment_type', 'amount', 'payment_date']

    def update(self, instance, validated_data):
        # Allow changing status only from pending to paid
        if instance.status != Payment.PaymentStatus.PENDING:
            raise serializers.ValidationError("Only pending payments can be updated.")
        new_status = validated_data.get('status', None)
        if new_status and new_status == Payment.PaymentStatus.PAID:
            instance.status = new_status
            instance.payment_date = timezone.now()
            instance.save()
            return instance
        raise serializers.ValidationError("Invalid status transition.")
```

### FILE: library/filters.py
```python
import django_filters
from django.contrib.auth import get_user_model
from .models import Borrowing

User = get_user_model()


class BorrowingFilter(django_filters.FilterSet):
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        field_name='user',
        to_field_name='id',
        help_text='Filter by user ID'
    )
    actual_return_date = django_filters.DateTimeFromToRangeFilter()
    actual_return_date_gt = django_filters.DateTimeFilter(field_name='actual_return_date', lookup_expr='gt')
    actual_return_date_lt = django_filters.DateTimeFilter(field_name='actual_return_date', lookup_expr='lt')

    class Meta:
        model = Borrowing
        fields = ['user', 'actual_return_date']
```

### FILE: library/views.py
```python
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from .models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingSerializer,
    BorrowingCreateSerializer,
    ReturnBookSerializer,
    PaymentSerializer
)
from .filters import BorrowingFilter


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(total_copies=serializer.validated_data.get('total_copies', 1),
                        available_copies=serializer.validated_data.get('total_copies', 1))


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    filterset_class = BorrowingFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return BorrowingCreateSerializer
        if self.action == 'return_book':
            return ReturnBookSerializer
        return BorrowingSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    @action(detail=True, methods=['post'], url_path='return')
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.actual_return_date:
            return Response({"detail": "Book already returned."}, status=status.HTTP_400_BAD_REQUEST)

        # Set return date
        borrowing.actual_return_date = timezone.now()
        borrowing.save()

        # Increase available copies
        book = borrowing.book
        book.available_copies += 1
        book.save()

        # Check if overdue and create fine payment if needed
        if borrowing.is_overdue and not Payment.objects.filter(borrowing=borrowing, payment_type='fine').exists():
            days_late = (borrowing.actual_return_date - borrowing.expected_return_date).days
            fine_amount = Decimal(days_late * settings.FINE_PER_DAY)
            Payment.objects.create(
                borrowing=borrowing,
                payment_type=Payment.PaymentType.FINE,
                amount=fine_amount,
                status=Payment.PaymentStatus.PENDING
            )

        return Response(BorrowingSerializer(borrowing).data, status=status.HTTP_200_OK)


class PaymentViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(borrowing__user=self.request.user)
        return queryset

    def get_permissions(self):
        if self.action in ['update', 'partial_update']:
            # Only owners can update (mark as paid)
            # We'll let the serializer handle status change, but check ownership
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH'] and not request.user.is_staff:
            if obj.borrowing.user != request.user:
                self.permission_denied(request, message="You do not own this payment.")
```

### FILE: library/urls.py
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from .views import BookViewSet, BorrowingViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'borrowings', BorrowingViewSet)
router.register(r'payments', PaymentViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="Library Service API",
        default_version='v1',
        description="API for borrowing books and managing payments",
        contact=openapi.Contact(email="support@library.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('doc/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('doc/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('', include(router.urls)),
]
```

### FILE: library/admin.py
```python
from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'isbn', 'total_copies', 'available_copies', 'borrowing_fee']
    search_fields = ['title', 'author', 'isbn']

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date']
    list_filter = ['borrow_date', 'actual_return_date', 'user']
    search_fields = ['user__email', 'book__title']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'borrowing', 'payment_type', 'amount', 'status', 'payment_date']
    list_filter = ['payment_type', 'status', 'payment_date']
```

### FILE: library/apps.py
```python
from django.apps import AppConfig

class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'library'
```

### FILE: library_service/wsgi.py
```python
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_wsgi_application()
```

### FILE: library_service/asgi.py
```python
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_service.settings')
application = get_asgi_application()