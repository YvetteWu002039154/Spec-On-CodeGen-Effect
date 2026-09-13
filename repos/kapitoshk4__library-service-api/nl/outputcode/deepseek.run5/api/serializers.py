from rest_framework import serializers
from .models import Book, Borrowing, Payment
from django.utils import timezone
from datetime import date

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'cover', 'inventory', 'daily_fee']

class BorrowingSerializer(serializers.ModelSerializer):
    book_title = serializers.ReadOnlyField(source='book.title')
    user_email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = Borrowing
        fields = ['id', 'user', 'book', 'borrow_date', 'expected_return_date',
                  'actual_return_date', 'is_active', 'book_title', 'user_email']
        read_only_fields = ['user', 'actual_return_date', 'is_active']

    def validate(self, data):
        book = data['book']
        if book.inventory <= 0:
            raise serializers.ValidationError("Book is not available (inventory 0).")
        borrow_date = data['borrow_date']
        expected_return = data['expected_return_date']
        if expected_return < borrow_date:
            raise serializers.ValidationError("Expected return date cannot be before borrow date.")
        return data

    def create(self, validated_data):
        book = validated_data['book']
        user = self.context['request'].user
        # Decrement inventory
        book.inventory -= 1
        book.save()

        borrowing = Borrowing.objects.create(
            user=user,
            book=book,
            borrow_date=validated_data['borrow_date'],
            expected_return_date=validated_data['expected_return_date']
        )
        return borrowing

class ReturnBorrowingSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField(required=True)

    def validate_actual_return_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Return date cannot be in the future.")
        return value

class PaymentSerializer(serializers.ModelSerializer):
    borrowing_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'borrowing', 'amount', 'payment_date', 'payment_type', 'status', 'borrowing_id']
        read_only_fields = ['id', 'borrowing', 'amount', 'payment_date', 'payment_type', 'status']

    def validate(self, data):
        borrowing_id = data.pop('borrowing_id')
        try:
            borrowing = Borrowing.objects.get(id=borrowing_id)
        except Borrowing.DoesNotExist:
            raise serializers.ValidationError("Borrowing not found.")

        # Only active borrowings can have rental payment made.
        if not borrowing.is_active:
            raise serializers.ValidationError("Borrowing is already returned; cannot make rental payment.")

        # Check if a rental payment already exists for this borrowing
        if borrowing.payments.filter(payment_type='RENTAL').exists():
            raise serializers.ValidationError("Rental payment already exists for this borrowing.")

        data['borrowing'] = borrowing
        data['user'] = self.context['request'].user
        # Calculate rental amount
        days = (borrowing.expected_return_date - borrowing.borrow_date).days
        if days < 1:
            days = 1
        data['amount'] = borrowing.book.daily_fee * days
        data['payment_type'] = 'RENTAL'
        return data

    def create(self, validated_data):
        return Payment.objects.create(**validated_data)

