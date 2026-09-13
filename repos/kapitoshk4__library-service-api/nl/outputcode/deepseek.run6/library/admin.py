from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'daily_fee', 'fine_per_day')
    search_fields = ('title', 'author')

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date', 'is_active')
    list_filter = ('is_active', 'actual_return_date', 'user')
    search_fields = ('user__username', 'book__title')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('borrowing', 'amount', 'payment_type', 'status', 'created_at')
    list_filter = ('payment_type', 'status', 'created_at')
