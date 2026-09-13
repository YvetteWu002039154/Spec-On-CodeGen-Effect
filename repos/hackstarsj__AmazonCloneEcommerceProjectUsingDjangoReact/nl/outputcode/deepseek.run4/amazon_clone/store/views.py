from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from .models import Product, Category
from cart.cart import Cart

def product_list(request):
    query = request.GET.get('q')
    category_slug = request.GET.get('category')
    products = Product.objects.all()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        # include subcategories
        descendants = category.get_descendants(include_self=True)
        products = products.filter(category__in=descendants)
    categories = Category.objects.filter(parent=None)
    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'selected_category': category_slug,
        'query': query
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'store/product_detail.html', {'product': product})

