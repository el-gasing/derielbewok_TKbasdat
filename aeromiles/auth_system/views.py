from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .forms import LoginForm, MemberRegistrationForm, StaffRegistrationForm
from .models import Member, Staff


@require_http_methods(["GET", "POST"])
def login_view(request):
    """View untuk login"""
    if request.user.is_authenticated:
        return redirect('auth_system:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Selamat datang, {user.first_name or user.username}!')
            return redirect('auth_system:dashboard')
        else:
            messages.error(request, 'Username atau password salah.')
    else:
        form = LoginForm()
    
    return render(request, 'auth_system/login.html', {'form': form})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """View untuk logout"""
    logout(request)
    messages.success(request, 'Anda telah berhasil logout.')
    return redirect('auth_system:login')


@login_required(login_url='auth_system:login')
def dashboard_view(request):
    """View untuk dashboard setelah login"""
    context = {}
    user = request.user
    
    # Check if user is member
    try:
        member = Member.objects.get(user=user)
        context['user_type'] = 'member'
        context['member'] = member
    except Member.DoesNotExist:
        pass
    
    # Check if user is staff
    try:
        staff = Staff.objects.get(user=user)
        context['user_type'] = 'staff'
        context['staff'] = staff
    except Staff.DoesNotExist:
        pass
    
    return render(request, 'auth_system/dashboard.html', context)


@require_http_methods(["GET", "POST"])
def register_member_view(request):
    """View untuk registrasi Member"""
    if request.user.is_authenticated:
        return redirect('auth_system:dashboard')
    
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Akun Member berhasil dibuat! Selamat datang!')
            return redirect('auth_system:dashboard')
        else:
            messages.error(request, 'Ada kesalahan dalam registrasi. Silakan cek lagi.')
    else:
        form = MemberRegistrationForm()
    
    return render(request, 'auth_system/register_member.html', {'form': form})


@require_http_methods(["GET", "POST"])
def register_staff_view(request):
    """View untuk registrasi Staff"""
    if request.user.is_authenticated:
        return redirect('auth_system:dashboard')
    
    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Akun Staff berhasil dibuat! Selamat datang!')
            return redirect('auth_system:dashboard')
        else:
            messages.error(request, 'Ada kesalahan dalam registrasi. Silakan cek lagi.')
    else:
        form = StaffRegistrationForm()
    
    return render(request, 'auth_system/register_staff.html', {'form': form})
