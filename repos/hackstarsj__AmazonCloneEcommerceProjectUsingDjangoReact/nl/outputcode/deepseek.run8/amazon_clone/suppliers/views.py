from django.shortcuts import render, get_object_or_404
from .models import Supplier

def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'suppliers/supplier_list.html', {{'suppliers': suppliers}})

def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    return render(request, 'suppliers/supplier_detail.html', {{'supplier': supplier}})
