import django_filters
from .models import Borrowing, Book

class BorrowingFilter(django_filters.FilterSet):
    user_id = django_filters.NumberFilter(field_name='user_id')
    actual_return_date = django_filters.DateFromToRangeFilter(field_name='actual_return_date')

    class Meta:
        model = Borrowing
        fields = ['user_id', 'actual_return_date', 'is_active']

