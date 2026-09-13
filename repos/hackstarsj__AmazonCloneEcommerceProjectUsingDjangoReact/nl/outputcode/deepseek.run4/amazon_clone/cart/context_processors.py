from .cart import Cart

def cart_processor(request):
    return {'cart': Cart(request)}

# add to settings templates context_processors:
# 'cart.context_processors.cart_processor'

