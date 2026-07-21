# =========================
# Admin
# =========================

from api.models import Book, Borrowing, Payment
from django.contrib import admin

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "inventory", "daily_fee")
    search_fields = ("title", "author")
    list_filter = ("author",)
    ordering = ("title",)


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "book", "borrow_date", "expected_return_date", "actual_return_date")
    list_filter = ("actual_return_date", "borrow_date")
    search_fields = ("user__username", "user__email", "book__title", "book__author")
    ordering = ("-borrow_date", "-id")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "borrowing", "payment_type", "status", "amount", "created_at", "paid_at")
    list_filter = ("status", "payment_type", "created_at")
    search_fields = ("borrowing__user__username", "borrowing__book__title", "borrowing__book__author")
    ordering = ("-created_at", "-id")
