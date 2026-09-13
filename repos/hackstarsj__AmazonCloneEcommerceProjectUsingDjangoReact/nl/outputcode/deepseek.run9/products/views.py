from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Category, Product
from .forms import ProductSearchForm


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.all()
    query = request.GET.get('query', '')
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    return render(request, 'products/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'query': query,
    })


def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug)
    return render(request, 'products/product/detail.html', {'product': product})

