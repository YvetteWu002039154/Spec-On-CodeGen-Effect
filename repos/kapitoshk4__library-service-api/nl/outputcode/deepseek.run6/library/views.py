from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Book, Borrowing, Payment
from .serializers import (
    BookSerializer,
    BorrowingSerializer,
    BorrowingCreateSerializer,
    ReturnSerializer,
    PaymentSerializer,
)
from .filters import BorrowingFilter
from datetime import date
from decimal import Decimal

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['title', 'author']

class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BorrowingFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return BorrowingCreateSerializer
        if self.action == 'return_book':
            return ReturnSerializer
        return BorrowingSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(request_body=ReturnSerializer)
    @action(detail=True, methods=['post'], url_path='return')
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        if borrowing.actual_return_date is not None:
            return Response(
                {'detail': 'Book already returned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Perform return
        borrowing.actual_return_date = date.today()
        borrowing.is_active = False
        borrowing.save()

        # Check if overdue and create fine if needed
        if borrowing.actual_return_date > borrowing.expected_return_date:
            overdue_days = (borrowing.actual_return_date - borrowing.expected_return_date).days
            fine_amount = borrowing.book.fine_per_day * overdue_days
            # Ensure no duplicate fine
            if not borrowing.payments.filter(payment_type='FINE').exists():
                Payment.objects.create(
                    borrowing=borrowing,
                    amount=fine_amount,
                    payment_type='FINE',
                )
        return Response(BorrowingSerializer(borrowing).data)

    def list(self, request, *args, **kwargs):
        # Users can see only their own borrowings unless admin
        queryset = self.filter_queryset(self.get_queryset())
        if not request.user.is_staff:
            queryset = queryset.filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(borrowing__user=self.request.user)
        return queryset

