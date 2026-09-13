from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Product, Category
from .forms import ProductSearchForm

def product_list(request):
    products = Product.objects.filter(is_active=True).order_by('-id')
    form = ProductSearchForm(request.GET)
    query = request.GET.get('query')
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_id:
        products = products.filter(category_id=category_id)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    categories = Category.objects.all()
    return render(request, 'products/product_list.html', {{
        'products': products,
        'categories': categories,
        'form': form,
    }})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'products/product_detail.html', {{'product': product}})

def product_search(request):
    return product_list(request)
