# File: orders/forms.py
from django import forms

class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(widget=forms.Textarea)