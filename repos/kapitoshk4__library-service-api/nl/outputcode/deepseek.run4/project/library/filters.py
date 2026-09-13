import django_filters
from .models import Borrowing, Payment, Book

class BorrowingFilter(django_filters.FilterSet):
    actual_return_date = django_filters.DateFilter()
    actual_return_date__gte = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='gte')
    actual_return_date__lte = django_filters.DateFilter(field_name='actual_return_date', lookup_expr='lte')
    user = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    user_id = django_filters.NumberFilter(field_name='user__id')
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = Borrowing
        fields = ['actual_return_date', 'user', 'is_active', 'user_id']

class PaymentFilter(django_filters.FilterSet):
    user = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=Payment.STATUS_CHOICES)
    payment_type = django_filters.ChoiceFilter(choices=Payment.TYPE_CHOICES)

    class Meta:
        model = Payment
        fields = ['user', 'status', 'payment_type']

class BookFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Book
        fields = ['title', 'author']

