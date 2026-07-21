# =========================
# Filters
# =========================

from django_filters import rest_framework as filters

from api.models import Borrowing, Payment, Book

class BorrowingFilter(filters.FilterSet):
    actual_return_date = filters.DateFilter(field_name="actual_return_date")
    user = filters.NumberFilter(field_name="user_id")

    class Meta:
        model = Borrowing
        fields = ["actual_return_date", "user"]


class PaymentFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    payment_type = filters.CharFilter(field_name="payment_type")
    borrowing = filters.NumberFilter(field_name="borrowing_id")

    class Meta:
        model = Payment
        fields = ["status", "payment_type", "borrowing"]


class BookFilter(filters.FilterSet):
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    author = filters.CharFilter(field_name="author", lookup_expr="icontains")

    class Meta:
        model = Book
        fields = ["title", "author"]
