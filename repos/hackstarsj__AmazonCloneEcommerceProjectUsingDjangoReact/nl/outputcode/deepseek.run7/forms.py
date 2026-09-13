# =============================================
# forms.py
# =============================================
from django import forms
from .models import CartItem

class CartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ['quantity']

class OrderCheckoutForm(forms.Form):
    shipping_address = forms.CharField(widget=forms.Textarea)
    payment_method = forms.ChoiceField(choices=[('dummy', 'Dummy Payment')])  # placeholder
