import django_filters
from django.contrib.auth import get_user_model
from .models import Borrowing

User = get_user_model()


class BorrowingFilter(django_filters.FilterSet):
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        field_name='user',
        to_field_name='id',
        help_text='Filter by user ID'
    )
    actual_return_date = django_filters.DateTimeFromToRangeFilter()
    actual_return_date_gt = django_filters.DateTimeFilter(field_name='actual_return_date', lookup_expr='gt')
    actual_return_date_lt = django_filters.DateTimeFilter(field_name='actual_return_date', lookup_expr='lt')

    class Meta:
        model = Borrowing
        fields = ['user', 'actual_return_date']

