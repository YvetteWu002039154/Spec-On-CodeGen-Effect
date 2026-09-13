import django_filters
from .models import Borrowing

class BorrowingFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='user__id')
    actual_return_date_after = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='gte')
    actual_return_date_before = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='lte')

    class Meta:
        model = Borrowing
        fields = ['user', 'actual_return_date_after', 'actual_return_date_before']

