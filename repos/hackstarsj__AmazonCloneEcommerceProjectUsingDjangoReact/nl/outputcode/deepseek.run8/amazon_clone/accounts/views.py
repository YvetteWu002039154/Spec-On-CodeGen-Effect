from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, AuthenticationForm

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('products_root:product_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {{'form': form}})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('products_root:product_list')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {{'form': form}})

def logout_view(request):
    logout(request)
    return redirect('products_root:product_list')

@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {{'user': request.user}})
