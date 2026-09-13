# --- models.py ---
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='US')
    role = models.CharField(max_length=20, choices=[('customer', 'Customer'), ('admin', 'Admin')], default='customer')

    def __str__(self):
        return self.user.username

class Category(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_list_by_category', args=[self.slug])

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Warehouse(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.slug])

    @property
    def total_stock(self):
        return self.stock_entries.aggregate(total=models.Sum('quantity'))['total'] or 0

    def is_in_stock(self):
        return self.total_stock > 0

class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_entries')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_entries')
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f"{self.product.name} in {self.warehouse.name}: {self.quantity}"

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def total_price(self):
        return self.product.price * self.quantity

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            from uuid import uuid4
            self.order_number = uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_number}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        return self.price * self.quantity

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('shipped', 'Shipped'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    po_number = models.CharField(max_length=20, unique=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.po_number:
            from uuid import uuid4
            self.po_number = f"PO-{uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.po_number

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    def total_cost(self):
        return self.quantity * self.unit_cost

# --- forms.py ---
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Order, CartItem, PurchaseOrder, Supplier, Warehouse, Stock

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    address_line1 = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    zip_code = forms.CharField(max_length=20, required=False)
    country = forms.CharField(max_length=100, initial='US', required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'phone', 'address_line1', 'city', 'state', 'zip_code', 'country')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                phone=self.cleaned_data.get('phone', ''),
                address_line1=self.cleaned_data.get('address_line1', ''),
                city=self.cleaned_data.get('city', ''),
                state=self.cleaned_data.get('state', ''),
                zip_code=self.cleaned_data.get('zip_code', ''),
                country=self.cleaned_data.get('country', 'US'),
            )
        return user

class ProductSearchForm(forms.Form):
    query = forms.CharField(required=False, label='Search')
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False, empty_label='All Categories')

class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)
    product_id = forms.IntegerField(widget=forms.HiddenInput)

class CheckoutForm(forms.Form):
    address_line1 = forms.CharField(max_length=255)
    address_line2 = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=100)
    state = forms.CharField(max_length=100)
    zip_code = forms.CharField(max_length=20)
    country = forms.CharField(max_length=100)

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'image', 'is_active']

class StockUpdateForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['warehouse', 'quantity']

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = '__all__'

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'warehouse', 'status', 'expected_delivery']

class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity', 'unit_cost']

# --- admin.py ---
from django.contrib import admin
from .models import (
    Profile, Category, Product, Stock, CartItem, Order, OrderItem,
    Supplier, Warehouse, PurchaseOrder, PurchaseOrderItem
)

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'role']

class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'parent']

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'is_active', 'total_stock']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description']

class StockAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity']

class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    inlines = [OrderItemInline]

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'warehouse', 'status', 'total_cost', 'expected_delivery']
    list_filter = ['status', 'supplier']
    inlines = [PurchaseOrderItemInline]

admin.site.register(Profile, ProfileAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Stock, StockAdmin)
admin.site.register(CartItem, CartItemAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Supplier)
admin.site.register(Warehouse)
admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
admin.site.register(PurchaseOrderItem)

# --- views.py ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Product, Category, CartItem, Order, OrderItem, Stock, Warehouse, PurchaseOrder, PurchaseOrderItem, Supplier, Profile
from .forms import (
    UserRegistrationForm, ProductSearchForm, CartUpdateForm, CheckoutForm,
    ProductForm, StockUpdateForm, SupplierForm, WarehouseForm,
    PurchaseOrderForm, PurchaseOrderItemForm
)

def home(request):
    search_form = ProductSearchForm(request.GET)
    products = Product.objects.filter(is_active=True)
    query = request.GET.get('query', '')
    category = request.GET.get('category', '')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category:
        products = products.filter(category__id=category)
    categories = Category.objects.filter(parent=None)
    return render(request, 'home.html', {
        'products': products[:20],
        'search_form': search_form,
        'categories': categories,
    })

def product_list_by_category(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True)
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        # include subcategories
        subcategory_ids = category.children.all().values_list('id', flat=True)
        products = products.filter(Q(category=category) | Q(category__id__in=subcategory_ids))
    search_form = ProductSearchForm(request.GET)
    query = request.GET.get('query')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'product_list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'search_form': search_form,
    })

def product_detail(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug, is_active=True)
    stocks = product.stock_entries.all()
    return render(request, 'product_detail.html', {'product': product, 'stocks': stocks})

def signup_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def view_cart(request):
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)
    else:
        cart_items = get_session_cart(request)
    total = sum(item.product.price * item.quantity if hasattr(item, 'product') else item['price'] * item['quantity'] for item in cart_items)
    return render(request, 'cart/cart.html', {'cart_items': cart_items, 'total': total})

def get_session_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    for product_id, quantity in cart.items():
        product = Product.objects.filter(pk=product_id, is_active=True).first()
        if product:
            cart_items.append({'product': product, 'quantity': quantity, 'price': product.price})
    return cart_items

def add_to_cart(request):
    if request.method == 'POST' or request.GET:
        product_id = request.POST.get('product_id') or request.GET.get('product_id')
        quantity = int(request.POST.get('quantity', 1) or request.GET.get('quantity', 1))
        if request.user.is_authenticated:
            product = get_object_or_404(Product, pk=product_id, is_active=True)
            cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
            if not created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()
        else:
            cart = request.session.get('cart', {})
            if product_id in cart:
                cart[product_id] += quantity
            else:
                cart[product_id] = quantity
            request.session['cart'] = cart
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'count': len(cart_items_count(request))})
        return redirect('view_cart')
    return redirect('home')

def cart_items_count(request):
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user).aggregate(total=Sum('quantity'))['total'] or 0
    else:
        cart = request.session.get('cart', {})
        return sum(cart.values()) if cart else 0

def remove_from_cart(request, product_id):
    if request.user.is_authenticated:
        CartItem.objects.filter(user=request.user, product_id=product_id).delete()
    else:
        cart = request.session.get('cart', {})
        cart.pop(str(product_id), None)
        request.session['cart'] = cart
    return redirect('view_cart')

def update_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        if request.user.is_authenticated:
            cart_item = CartItem.objects.filter(user=request.user, product_id=product_id).first()
            if cart_item:
                if quantity > 0:
                    cart_item.quantity = quantity
                    cart_item.save()
                else:
                    cart_item.delete()
        else:
            cart = request.session.get('cart', {})
            if quantity > 0:
                cart[str(product_id)] = quantity
            else:
                cart.pop(str(product_id), None)
            request.session['cart'] = cart
    return redirect('view_cart')

@login_required
def checkout(request):
    # Transfer session cart to database cart for logged-in user (if any)
    if request.user.is_authenticated:
        session_cart = request.session.get('cart', {})
        for product_id, qty in session_cart.items():
            product = Product.objects.filter(pk=product_id, is_active=True).first()
            if product:
                cart_item, _ = CartItem.objects.get_or_create(user=request.user, product=product)
                cart_item.quantity += qty
                cart_item.save()
        request.session['cart'] = {}
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items:
        messages.warning(request, 'Your cart is empty')
        return redirect('view_cart')
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            address = f"{form.cleaned_data['address_line1']}, {form.cleaned_data['city']}, {form.cleaned_data['state']} {form.cleaned_data['zip_code']}, {form.cleaned_data['country']}"
            # Create order
            total = sum(item.total_price() for item in cart_items)
            order = Order.objects.create(user=request.user, total_amount=total, shipping_address=address)
            for item in cart_items:
                # Check stock and deduct from default warehouse (first warehouse)
                stock = Stock.objects.filter(product=item.product).first()
                if stock and stock.quantity >= item.quantity:
                    stock.quantity -= item.quantity
                    stock.save()
                elif not stock or stock.quantity < item.quantity:
                    messages.error(request, f"Insufficient stock for {item.product.name}")
                    return redirect('view_cart')
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    price=item.product.price,
                )
                item.delete()
            messages.success(request, f'Order {order.order_number} placed successfully')
            return redirect('order_history')
    else:
        # pre-fill form with user profile data
        profile = request.user.profile
        initial = {
            'address_line1': profile.address_line1,
            'city': profile.city,
            'state': profile.state,
            'zip_code': profile.zip_code,
            'country': profile.country,
        }
        form = CheckoutForm(initial=initial)
    total = sum(item.total_price() for item in cart_items)
    return render(request, 'checkout.html', {'form': form, 'cart_items': cart_items, 'total': total})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/history.html', {'orders': orders})

@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'orders/detail.html', {'order': order})

# Admin views
def admin_required(view_func):
    return user_passes_test(lambda u: u.profile.role == 'admin' or u.is_superuser, login_url='login')(view_func)

@admin_required
@login_required
def inventory_dashboard(request):
    low_stock_threshold = 5
    products = Product.objects.filter(is_active=True).annotate(
        total_stock=Sum('stock_entries__quantity')
    ).filter(total_stock__lt=low_stock_threshold)
    return render(request, 'admin/inventory_dashboard.html', {'products': products})

@admin_required
@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'admin/supplier_list.html', {'suppliers': suppliers})

@admin_required
@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'admin/supplier_form.html', {'form': form})

@admin_required
@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'admin/supplier_form.html', {'form': form, 'supplier': supplier})

@admin_required
@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.delete()
    return redirect('supplier_list')

@admin_required
@login_required
def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, 'admin/warehouse_list.html', {'warehouses': warehouses})

@admin_required
@login_required
def warehouse_create(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('warehouse_list')
    else:
        form = WarehouseForm()
    return render(request, 'admin/warehouse_form.html', {'form': form})

@admin_required
@login_required
def warehouse_edit(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    if request.method == 'POST':
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            form.save()
            return redirect('warehouse_list')
    else:
        form = WarehouseForm(instance=warehouse)
    return render(request, 'admin/warehouse_form.html', {'form': form, 'warehouse': warehouse})

@admin_required
@login_required
def warehouse_delete(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    warehouse.delete()
    return redirect('warehouse_list')

@admin_required
@login_required
def purchase_order_list(request):
    pos = PurchaseOrder.objects.all().order_by('-created_at')
    return render(request, 'admin/po_list.html', {'purchase_orders': pos})

@admin_required
@login_required
def purchase_order_detail(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    return render(request, 'admin/po_detail.html', {'po': po})

@admin_required
@login_required
def purchase_order_create(request):
    if request.method == 'POST':
        po_form = PurchaseOrderForm(request.POST)
        # need to handle inline items via formsets
        from django.forms import inlineformset_factory
        ItemFormSet = inlineformset_factory(PurchaseOrder, PurchaseOrderItem, form=PurchaseOrderItemForm, extra=1, can_delete=True)
        if po_form.is_valid():
            po = po_form.save()
            formset = ItemFormSet(request.POST, instance=po)
            if formset.is_valid():
                formset.save()
                # update total cost
                po.total_cost = sum(item.total_cost() for item in po.items.all())
                po.save()
                return redirect('purchase_order_detail', pk=po.pk)
        else:
            formset = ItemFormSet(request.POST)
    else:
        po_form = PurchaseOrderForm()
        from django.forms import inlineformset_factory
        ItemFormSet = inlineformset_factory(PurchaseOrder, PurchaseOrderItem, form=PurchaseOrderItemForm, extra=1, can_delete=True)
        formset = ItemFormSet()
    return render(request, 'admin/po_form.html', {'po_form': po_form, 'formset': formset})

@admin_required
@login_required
def purchase_order_receive(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if po.status == 'received':
        messages.info(request, 'Already received')
        return redirect('purchase_order_detail', pk=po.pk)
    # For each item, increase stock in the selected warehouse
    for item in po.items.all():
        stock, created = Stock.objects.get_or_create(product=item.product, warehouse=po.warehouse)
        stock.quantity += item.quantity
        stock.save()
    po.status = 'received'
    po.save()
    messages.success(request, 'Purchase order received, stock updated')
    return redirect('purchase_order_detail', pk=po.pk)

@admin_required
@login_required
def product_management(request):
    products = Product.objects.all()
    return render(request, 'admin/product_management.html', {'products': products})

@admin_required
@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            return redirect('product_management')
    else:
        form = ProductForm()
    return render(request, 'admin/product_form.html', {'form': form})

@admin_required
@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_management')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin/product_form.html', {'form': form, 'product': product})

@admin_required
@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = False
    product.save()
    return redirect('product_management')

@admin_required
@login_required
def stock_update(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)
    stocks = Stock.objects.filter(product=product)
    if request.method == 'POST':
        form = StockUpdateForm(request.POST)
        if form.is_valid():
            warehouse = form.cleaned_data['warehouse']
            quantity = form.cleaned_data['quantity']
            stock, created = Stock.objects.get_or_create(product=product, warehouse=warehouse)
            stock.quantity = quantity
            stock.save()
            return redirect('product_management')
    else:
        form = StockUpdateForm(initial={'warehouse': Warehouse.objects.first()})
    return render(request, 'admin/stock_form.html', {'form': form, 'product': product, 'stocks': stocks})

# --- urls.py (app urls) ---
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('category/<slug:category_slug>/', views.product_list_by_category, name='product_list_by_category'),
    path('category/', views.product_list_by_category, name='product_list'),
    path('product/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/count/', views.cart_items_count, name='cart_count'), # for AJAX
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    # Admin Inventory/Management
    path('admin/inventory/', views.inventory_dashboard, name='inventory_dashboard'),
    path('admin/suppliers/', views.supplier_list, name='supplier_list'),
    path('admin/suppliers/create/', views.supplier_create, name='supplier_create'),
    path('admin/suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('admin/suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    path('admin/warehouses/', views.warehouse_list, name='warehouse_list'),
    path('admin/warehouses/create/', views.warehouse_create, name='warehouse_create'),
    path('admin/warehouses/<int:pk>/edit/', views.warehouse_edit, name='warehouse_edit'),
    path('admin/warehouses/<int:pk>/delete/', views.warehouse_delete, name='warehouse_delete'),
    path('admin/purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('admin/purchase-orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('admin/purchase-orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('admin/purchase-orders/<int:pk>/receive/', views.purchase_order_receive, name='purchase_order_receive'),
    path('admin/products/', views.product_management, name='product_management'),
    path('admin/products/create/', views.product_create, name='product_create'),
    path('admin/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('admin/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('admin/products/<int:product_pk>/stock/', views.stock_update, name='stock_update'),
]

# --- settings.py additions ---
# To be included in project settings:
# INSTALLED_APPS = [ ..., 'amazon_clone', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles']
# LOGIN_URL = 'login'
# LOGIN_REDIRECT_URL = 'home'
# MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'media'

# --- templates (not Python, omitted) ---
# The views reference templates: home.html, product_list.html, product_detail.html,
# registration/signup.html, registration/login.html, cart/cart.html, checkout.html,
# orders/history.html, orders/detail.html, admin/inventory_dashboard.html,
# admin/supplier_list.html, admin/supplier_form.html, admin/warehouse_list.html,
# admin/warehouse_form.html, admin/po_list.html, admin/po_detail.html,
# admin/po_form.html, admin/product_management.html, admin/product_form.html,
# admin/stock_form.html. They can be created as needed.