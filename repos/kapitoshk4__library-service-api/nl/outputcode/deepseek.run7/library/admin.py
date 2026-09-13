from django.contrib import admin
from .models import Book, Borrowing, Payment

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'isbn', 'total_copies', 'available_copies', 'borrowing_fee']
    search_fields = ['title', 'author', 'isbn']

@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'book', 'borrow_date', 'expected_return_date', 'actual_return_date']
    list_filter = ['borrow_date', 'actual_return_date', 'user']
    search_fields = ['user__email', 'book__title']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'borrowing', 'payment_type', 'amount', 'status', 'payment_date']
    list_filter = ['payment_type', 'status', 'payment_date']

