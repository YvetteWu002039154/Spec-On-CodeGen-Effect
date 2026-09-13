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

