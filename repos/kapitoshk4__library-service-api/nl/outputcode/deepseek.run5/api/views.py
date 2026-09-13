from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Book, Borrowing, Payment
from .serializers import BookSerializer, BorrowingSerializer, ReturnBorrowingSerializer, PaymentSerializer
from .permissions import IsAdminOrOwner
from .filters import BorrowingFilter
from datetime import date

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author']
    ordering_fields = ['title', 'author']

class BorrowingViewSet(viewsets.ModelViewSet):
    serializer_class = BorrowingSerializer
    permission_classes = [IsAdminOrOwner]
    filterset_class = BorrowingFilter
    ordering_fields = ['borrow_date', 'expected_return_date', 'actual_return_date']

    def get_queryset(self):
        if self.request.user.is_staff:
            return Borrowing.objects.all()
        return Borrowing.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='return')
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if not borrowing.is_active:
            return Response({'detail': 'This borrowing has already been returned.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReturnBorrowingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actual_return_date = serializer.validated_data['actual_return_date']

        borrowing.actual_return_date = actual_return_date
        borrowing.save()

        # Return book to inventory
        book = borrowing.book
        book.inventory += 1
        book.save()

        # Create fine payment if overdue
        if actual_return_date > borrowing.expected_return_date:
            overdue_days = (actual_return_date - borrowing.expected_return_date).days
            fine_amount = book.daily_fee * overdue_days * 2  # doubled daily fee as fine
            Payment.objects.create(
                user=borrowing.user,
                borrowing=borrowing,
                amount=fine_amount,
                payment_type='FINE',
                status='PENDING'
            )

        return Response(BorrowingSerializer(borrowing, context={'request': request}).data)

class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

