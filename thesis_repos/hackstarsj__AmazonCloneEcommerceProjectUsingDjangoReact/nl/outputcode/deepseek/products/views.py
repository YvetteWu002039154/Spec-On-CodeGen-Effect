# File: products/views.py
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Product, Category

class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(parent=None)
        return context

class CategoryDetailView(DetailView):
    model = Category
    template_name = 'products/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        # products in this category and subcategories
        subcategories = category.children.all()
        products = Product.objects.filter(category__in=[category] + list(subcategories), is_active=True)
        context['products'] = products
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

def product_search(request):
    query = request.GET.get('q', '')
    results = Product.objects.filter(is_active=True)
    if query:
        results = results.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query))
    return render(request, 'products/search_results.html', {'query': query, 'products': results})
