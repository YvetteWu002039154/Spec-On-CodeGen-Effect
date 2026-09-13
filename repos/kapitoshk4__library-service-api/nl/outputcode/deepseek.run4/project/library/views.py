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

