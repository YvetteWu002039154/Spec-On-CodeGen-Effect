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

