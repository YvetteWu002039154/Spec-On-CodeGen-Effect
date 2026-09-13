from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'inventory', 'daily_fee', 'fine_per_day')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_active')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'borrowing', 'amount', 'status', 'payment_type', 'payment_date')

