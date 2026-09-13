from rest_framework import serializers
from rest_framework.request import Request

from typing import Any, Dict
from datetime import date
from decimal import Decimal

from django.db import transaction

from api.models import Book, Borrowing, Payment

# =========================
# Business logic helpers
# =========================

def _days_between(start: date, end: date) -> int:
    delta = (end - start).days
    return max(0, int(delta))


def calculate_borrowing_amount(borrowing: Borrowing) -> Decimal:
    days = _days_between(borrowing.borrow_date, borrowing.expected_return_date)
    return (Decimal(days) * borrowing.book.daily_fee).quantize(Decimal("0.01"))


def calculate_fine_amount(borrowing: Borrowing, actual_return_date: date) -> Decimal:
    overdue_days = _days_between(borrowing.expected_return_date, actual_return_date)
    if overdue_days <= 0:
        return Decimal("0.00")
    fine_multiplier = Decimal("2.00")
    return (Decimal(overdue_days) * borrowing.book.daily_fee * fine_multiplier).quantize(Decimal("0.01"))


# =========================
# Serializers
# =========================


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title", "author", "inventory", "daily_fee"]


class BorrowingSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())

    class Meta:
        model = Borrowing
        fields = [
            "id",
            "user",
            "book",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
        ]
        read_only_fields = ["borrow_date", "actual_return_date"]

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        expected = attrs.get("expected_return_date")
        if expected is None:
            raise serializers.ValidationError({"expected_return_date": "Expected return date is required."})
        borrow_date = date.today()
        if expected < borrow_date:
            raise serializers.ValidationError({"expected_return_date": "Expected return date cannot be before borrow date."})
        book: Book = attrs.get("book")
        if book is None:
            raise serializers.ValidationError({"book": "Book is required."})
        if book.inventory <= 0:
            raise serializers.ValidationError({"book": "Book is out of stock."})
        return attrs

    def create(self, validated_data: Dict[str, Any]) -> Borrowing:
        request: Request = self.context["request"]
        user = request.user
        book: Book = validated_data["book"]
        expected = validated_data["expected_return_date"]

        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=book.pk)
            if book.inventory <= 0:
                raise serializers.ValidationError({"book": "Book is out of stock."})
            book.inventory -= 1
            book.save(update_fields=["inventory"])

            borrowing = Borrowing.objects.create(
                user=user,
                book=book,
                borrow_date=date.today(),
                expected_return_date=expected,
            )

            amount = calculate_borrowing_amount(borrowing)
            Payment.objects.create(
                borrowing=borrowing,
                payment_type=Payment.Type.BORROWING,
                status=Payment.Status.PENDING,
                amount=amount,
            )
        return borrowing


class BorrowingReturnSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField(required=False)

    def validate_actual_return_date(self, value: date) -> date:
        if value > date.today():
            raise serializers.ValidationError("Actual return date cannot be in the future.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "borrowing", "payment_type", "status", "amount", "created_at", "paid_at"]
        read_only_fields = ["created_at", "paid_at"]


class PaymentPaySerializer(serializers.Serializer):
    paid = serializers.BooleanField(default=True)

    def validate_paid(self, value: bool) -> bool:
        if value is not True:
            raise serializers.ValidationError("Only paying (paid=true) is supported.")
        return value
