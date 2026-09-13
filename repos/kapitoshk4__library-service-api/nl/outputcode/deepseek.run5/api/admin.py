from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'cover', 'inventory', 'daily_fee')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_active')
    list_filter = ('is_active', 'actual_return_date')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'borrowing', 'amount', 'payment_type', 'status', 'payment_date')
    list_filter = ('payment_type', 'status')
