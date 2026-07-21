# File: api/filters.py
import django_filters
from .models import Borrowing

class BorrowingFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='user_id', lookup_expr='exact')
    actual_return_date = django_filters.DateFilter(field_name='actual_return_date')

    class Meta:
        model = Borrowing
        fields = ['user', 'actual_return_date']