# File: api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Book, Borrowing, Payment
from datetime import date

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class BookSerializer(serializers.ModelSerializer):
    available_copies = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = ('id',)

    def get_available_copies(self, obj):
        return obj.available_copies()

class BorrowingListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    book = BookSerializer(read_only=True)
    is_active = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = '__all__'
        read_only_fields = ('id', 'user', 'book', 'borrow_date')

    def get_is_active(self, obj):
        return obj.is_active

    def get_is_overdue(self, obj):
        return obj.is_overdue

class BorrowingCreateSerializer(serializers.ModelSerializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Borrowing
        fields = ('book', 'expected_return_date', 'user')
        extra_kwargs = {'expected_return_date': {'required': True}}

    def validate(self, data):
        book = data['book']
        if book.available_copies() <= 0:
            raise serializers.ValidationError("No available copies of this book.")
        if data['expected_return_date'] <= date.today():
            raise serializers.ValidationError("Expected return date must be in the future.")
        return data

class BorrowingReturnSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField(default=date.today())

    def validate_actual_return_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Return date cannot be in the future.")
        return value

class PaymentSerializer(serializers.ModelSerializer):
    borrowing = serializers.PrimaryKeyRelatedField(queryset=Borrowing.objects.all())

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('id', 'payment_date', 'status')

class PaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('status',)