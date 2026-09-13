from rest_framework import serializers
from .models import Book, Borrowing, Payment
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

User = get_user_model()

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class BorrowingSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Borrowing
        fields = ['id', 'borrow_date', 'expected_return_date', 'actual_return_date',
                  'book', 'book_title', 'user', 'user_email', 'is_active']
        read_only_fields = ['borrow_date', 'is_active', 'user']

    def validate(self, data):
        if self.instance is None:  # creation
            book = data['book']
            if book.inventory <= 0:
                raise serializers.ValidationError("Book is out of stock.")
            data['user'] = self.context['request'].user
        return data

    def create(self, validated_data):
        book = validated_data['book']
        user = validated_data['user']
        duration = (validated_data['expected_return_date'] - date.today()).days
        if duration <= 0:
            raise serializers.ValidationError("Expected return date must be in the future.")
        with transaction.atomic():
            book.inventory -= 1
            book.save()
            borrowing = Borrowing.objects.create(**validated_data, borrow_date=date.today())
            fee_amount = book.daily_fee * duration
            Payment.objects.create(
                user=user,
                borrowing=borrowing,
                amount=fee_amount,
                payment_type='BORROWING_FEE',
                status='PENDING'
            )
            return borrowing

from django.db import transaction
class BorrowingReturnSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField()

    def validate_actual_return_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Return date cannot be in the future.")
        return value

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['user', 'amount', 'payment_type', 'borrowing', 'session_id', 'payment_date']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

