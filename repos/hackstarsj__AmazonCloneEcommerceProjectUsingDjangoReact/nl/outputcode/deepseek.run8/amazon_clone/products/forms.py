from django import forms
from .models import Product, Category

class ProductSearchForm(forms.Form):
    query = forms.CharField(required=False, label='Search')
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)
    min_price = forms.DecimalField(required=False, min_value=0)
    max_price = forms.DecimalField(required=False, min_value=0)
