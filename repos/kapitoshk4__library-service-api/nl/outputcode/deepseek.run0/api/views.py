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