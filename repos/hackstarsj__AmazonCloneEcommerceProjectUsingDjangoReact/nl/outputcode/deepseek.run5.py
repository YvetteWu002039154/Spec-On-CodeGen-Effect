# models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255)
    address = models.TextField()

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='products/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def total_stock(self):
        return sum(inv.quantity for inv in self.inventories.all())


class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventories')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='inventories')
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"


class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('ORDERED', 'Ordered'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled')
    ], default='PENDING')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"PO #{self.id} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        if self.pk:
            orig = PurchaseOrder.objects.get(pk=self.pk)
            if orig.status != 'RECEIVED' and self.status == 'RECEIVED':
                # update stock when received
                for item in self.items.all():
                    inv, created = Inventory.objects.get_or_create(
                        product=item.product,
                        warehouse=self.warehouse,
                        defaults={'quantity': 0}
                    )
                    inv.quantity += item.quantity
                    inv.save()
        super().save(*args, **kwargs)


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        return f"Anonymous Cart {self.id}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled')
    ], default='PENDING')
    shipping_address = models.TextField()
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.username


# admin.py
from django.contrib import admin
from .models import Category, Supplier, Warehouse, Product, Inventory, PurchaseOrder, PurchaseOrderItem, Cart, CartItem, Order, OrderItem, Profile

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Warehouse)

class InventoryInline(admin.TabularInline):
    model = Inventory
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'total_stock', 'active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [InventoryInline]

admin.site.register(Product, ProductAdmin)

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'warehouse', 'status', 'order_date')
    inlines = [PurchaseOrderItemInline]

admin.site.register(PurchaseOrder, PurchaseOrderAdmin)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order_date', 'status', 'total')
    inlines = [OrderItemInline]

admin.site.register(Order, OrderAdmin)
admin.site.register(Profile)


# forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Product, Order, Profile, PurchaseOrder, Supplier, Warehouse, PurchaseOrderItem, Inventory

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('address', 'phone')

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('name', 'description', 'price', 'category', 'image', 'active')

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ('supplier', 'warehouse', 'expected_delivery', 'status', 'notes')

class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ('product', 'quantity', 'unit_cost')

class InventoryUpdateForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ('quantity',)


# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, View
from django.urls import reverse_lazy, reverse
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Inventory, Warehouse, PurchaseOrder, Supplier
from .forms import UserRegistrationForm, ProfileForm, ProductForm, PurchaseOrderForm, PurchaseOrderItemForm, InventoryUpdateForm
from decimal import Decimal

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        cart_id = request.session.get('cart_id')
        if cart_id:
            cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()
            if not cart:
                cart = None
        else:
            cart = None
        if not cart:
            cart = Cart.objects.create()
            request.session['cart_id'] = cart.id
    return cart

class HomeView(ListView):
    model = Product
    template_name = 'store/home.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(active=True)
        query = self.request.GET.get('q')
        category_slug = self.request.GET.get('category')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['query'] = self.request.GET.get('q', '')
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'

class CartDetailView(View):
    def get(self, request):
        cart = get_or_create_cart(request)
        return render(request, 'store/cart.html', {'cart': cart})

class AddToCartView(View):
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id, active=True)
        cart = get_or_create_cart(request)
        quantity = int(request.POST.get('quantity', 1))
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product,
                                                           defaults={'quantity': quantity})
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        messages.success(request, f"{product.name} added to cart.")
        return redirect('store:cart')

class UpdateCartView(View):
    def post(self, request, item_id):
        item = get_object_or_404(CartItem, id=item_id, cart=get_or_create_cart(request))
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            item.delete()
        else:
            item.quantity = quantity
            item.save()
        return redirect('store:cart')

class RemoveCartItemView(View):
    def post(self, request, item_id):
        item = get_object_or_404(CartItem, id=item_id, cart=get_or_create_cart(request))
        item.delete()
        messages.success(request, "Item removed from cart.")
        return redirect('store:cart')

class CheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        cart = get_or_create_cart(request)
        if not cart.items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('store:cart')
        total = sum(item.quantity * item.product.price for item in cart.items.all())
        profile = Profile.objects.filter(user=request.user).first()
        return render(request, 'store/checkout.html', {'cart': cart, 'total': total, 'profile': profile})

    def post(self, request):
        cart = get_or_create_cart(request)
        if not cart.items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('store:cart')
        # Validate stock
        for item in cart.items.all():
            if item.product.total_stock() < item.quantity:
                messages.error(request, f"Insufficient stock for {item.product.name}. Only {item.product.total_stock()} left.")
                return redirect('store:cart')
        # Create order and deduct stock
        shipping_address = request.POST.get('address', '')
        if not shipping_address:
            messages.error(request, "Please provide a shipping address.")
            return redirect('store:checkout')
        order = Order.objects.create(user=request.user, shipping_address=shipping_address)
        total = Decimal('0.00')
        for item in cart.items.all():
            order_item = OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            total += item.quantity * item.product.price
            # Deduct stock from warehouse(s) – pick the one with highest stock
            inventories = item.product.inventories.order_by('-quantity')
            remaining = item.quantity
            for inv in inventories:
                if inv.quantity >= remaining:
                    inv.quantity -= remaining
                    inv.save()
                    remaining = 0
                    break
                else:
                    remaining -= inv.quantity
                    inv.quantity = 0
                    inv.save()
            if remaining > 0:
                # This shouldn't happen due to earlier check, but handle gracefully
                messages.error(request, f"Stock allocation error for {item.product.name}.")
                order.status = 'CANCELLED'
                order.save()
                return redirect('store:cart')
        order.total = total
        order.save()
        # Clear cart
        cart.items.all().delete()
        if not request.user.is_authenticated:
            del request.session['cart_id']
        messages.success(request, "Order placed successfully.")
        return redirect('store:order_detail', pk=order.pk)

class OrderHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'store/order_history.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-order_date')

class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'store/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

class RegisterView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'store/register.html'
    success_url = reverse_lazy('store:home')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        Profile.objects.create(user=user)
        return redirect(self.success_url)

class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

# Admin inventory management views
class InventoryManagementView(StaffRequiredMixin, ListView):
    model = Product
    template_name = 'store/admin/inventory_list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        return Product.objects.all().order_by('name')

class ProductUpdateView(StaffRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'store/admin/product_form.html'
    success_url = reverse_lazy('store:admin_inventory')

class ProductCreateView(StaffRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'store/admin/product_form.html'
    success_url = reverse_lazy('store:admin_inventory')

class InventoryUpdateView(StaffRequiredMixin, UpdateView):
    model = Inventory
    form_class = InventoryUpdateForm
    template_name = 'store/admin/inventory_form.html'

    def get_success_url(self):
        return reverse('store:admin_inventory')

class PurchaseOrderListView(StaffRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'store/admin/purchase_order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

class PurchaseOrderCreateView(StaffRequiredMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'store/admin/purchase_order_form.html'
    success_url = reverse_lazy('store:admin_purchase_orders')

    def form_valid(self, form):
        self.object = form.save()
        return redirect(reverse('store:admin_purchase_order_detail', kwargs={'pk': self.object.pk}))

class PurchaseOrderDetailView(StaffRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'store/admin/purchase_order_detail.html'
    context_object_name = 'order'

class AddPurchaseOrderItemView(StaffRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(PurchaseOrder, pk=pk)
        form = PurchaseOrderItemForm(request.POST)
        if form.is_valid():
            PurchaseOrderItem.objects.create(
                purchase_order=order,
                product=form.cleaned_data['product'],
                quantity=form.cleaned_data['quantity'],
                unit_cost=form.cleaned_data['unit_cost']
            )
            messages.success(request, "Item added.")
        return redirect('store:admin_purchase_order_detail', pk=pk)

# Supplier and warehouse views similar (omitted for brevity; can be managed via Django admin)
# For full cloning, include CRUD for Supplier and Warehouse as well.


# urls.py
from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('cart/', views.CartDetailView.as_view(), name='cart'),
    path('cart/add/<int:product_id>/', views.AddToCartView.as_view(), name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.UpdateCartView.as_view(), name='update_cart'),
    path('cart/remove/<int:item_id>/', views.RemoveCartItemView.as_view(), name='remove_cart'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('orders/', views.OrderHistoryView.as_view(), name='order_history'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('register/', views.RegisterView.as_view(), name='register'),
    # Admin inventory URLs
    path('admin/inventory/', views.InventoryManagementView.as_view(), name='admin_inventory'),
    path('admin/inventory/product/add/', views.ProductCreateView.as_view(), name='admin_product_add'),
    path('admin/inventory/product/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='admin_product_edit'),
    path('admin/inventory/<int:pk>/update/', views.InventoryUpdateView.as_view(), name='admin_inventory_update'),
    path('admin/purchase-orders/', views.PurchaseOrderListView.as_view(), name='admin_purchase_orders'),
    path('admin/purchase-orders/create/', views.PurchaseOrderCreateView.as_view(), name='admin_purchase_order_create'),
    path('admin/purchase-orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='admin_purchase_order_detail'),
    path('admin/purchase-orders/<int:pk>/add-item/', views.AddPurchaseOrderItemView.as_view(), name='admin_purchase_order_add_item'),
    # Authentication (built-in)
    path('login/', auth_views.LoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='store:home'), name='logout'),
]

# Include the following in project's urls.py:
# path('accounts/profile/', RedirectView.as_view(url=reverse_lazy('store:order_history'))),
# path('', include('store.urls')),