# File: suppliers/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from .models import Supplier, PurchaseOrder

@staff_member_required
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'suppliers/supplier_list.html', {'suppliers': suppliers})

@staff_member_required
def purchase_order_list(request):
    orders = PurchaseOrder.objects.all()
    return render(request, 'suppliers/purchase_order_list.html', {'orders': orders})

@staff_member_required
def purchase_order_detail(request, po_id):
    order = get_object_or_404(PurchaseOrder, id=po_id)
    return render(request, 'suppliers/purchase_order_detail.html', {'order': order})

