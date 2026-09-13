from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Category, Product

def product_list(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    products = Product.objects.all()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category__in=category.get_descendants(include_self=True))
    categories = Category.objects.filter(parent=None)
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category_slug,
    }
    return render(request, 'products/product_list.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'products/product_detail.html', {'product': product})

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category__in=category.get_descendants(include_self=True))
    return render(request, 'products/category_detail.html', {'category': category, 'products': products})

# Helper method on Category model (added via monkey patching or model method)
def get_descendants(self, include_self=False):
    descendants = []
    if include_self:
        descendants.append(self)
    for child in self.children.all():
        descendants.extend(child.get_descendants(include_self=True))
    return descendants

# Monkey-patch
Category.get_descendants = get_descendants

