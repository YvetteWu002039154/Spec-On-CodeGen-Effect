# File: api/admin.py
from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'cover', 'inventory', 'daily_fee', 'fine_per_day')
    list_filter = ('cover',)
    search_fields = ('title', 'author')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_active')
    list_filter = ('actual_return_date', 'user')
    search_fields = ('user__username', 'book__title')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'borrowing', 'amount', 'payment_type', 'payment_date', 'status')
    list_filter = ('payment_type', 'status', 'payment_date')