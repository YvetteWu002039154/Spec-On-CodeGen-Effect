from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Book, Borrowing, Payment
from datetime import date

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class BorrowingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    book = BookSerializer(read_only=True)
    total_fee = serializers.SerializerMethodField()
    fine_amount = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = ('id', 'user', 'book', 'borrow_date', 'expected_return_date',
                  'actual_return_date', 'is_active', 'total_fee', 'fine_amount')

    def get_total_fee(self, obj):
        # Sum of all payments for this borrowing
        return sum(payment.amount for payment in obj.payments.all())

    def get_fine_amount(self, obj):
        # Sum of fine payments
        return sum(payment.amount for payment in obj.payments.filter(payment_type='FINE'))

class BorrowingCreateSerializer(serializers.ModelSerializer):
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(), source='book', write_only=True
    )

    class Meta:
        model = Borrowing
        fields = ('book_id',)

    def validate_book(self, book):
        if not book.is_available():
            raise serializers.ValidationError("Book is not available for borrowing")
        return book

    def create(self, validated_data):
        user = self.context['request'].user
        book = validated_data['book']
        borrowing = Borrowing.objects.create(
            user=user,
            book=book,
            borrow_date=date.today(),
            expected_return_date=date.today() + timedelta(days=30),
        )
        # Create payment for borrowing fee
        fee = book.daily_fee * (borrowing.expected_return_date - borrowing.borrow_date).days
        Payment.objects.create(
            borrowing=borrowing,
            amount=fee,
            payment_type='BORROWING',
        )
        return borrowing

class ReturnSerializer(serializers.Serializer):
    # No fields needed, just trigger return action
    pass

