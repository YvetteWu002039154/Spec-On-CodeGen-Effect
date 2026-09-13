from django import forms
from .models import CartItem

class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)

class UpdateCartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ['quantity']
