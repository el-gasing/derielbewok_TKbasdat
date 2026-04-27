from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import Http404
from django.core.paginator import Paginator
from django.db.models import Q
from functools import wraps
from datetime import date
from .forms import LoginForm, MemberRegistrationForm, StaffRegistrationForm, AddMemberForm, EditMemberForm, AddIdentityForm, EditIdentityForm
from .models import Member, Staff, Identity


def staff_required(view_func):
    """Decorator untuk memastikan hanya staff yang bisa akses"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth_system:login')
        
        try:
            Staff.objects.get(user=request.user)
            return view_func(request, *args, **kwargs)
        except Staff.DoesNotExist:
            messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
            return redirect('auth_system:dashboard')
    
    return wrapper


def member_required(view_func):
    """Decorator untuk memastikan hanya member yang bisa akses"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth_system:login')
        
        try:
            Member.objects.get(user=request.user)
            return view_func(request, *args, **kwargs)
        except Member.DoesNotExist:
            messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
            return redirect('auth_system:dashboard')
    
    return wrapper


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
    
    return render(request, 'auth/login.html', {'form': form})


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
    
    return render(request, 'dashboard.html', context)


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
    
    return render(request, 'auth/register_member.html', {'form': form})


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
    
    return render(request, 'auth/register_staff.html', {'form': form})


@staff_required
@require_http_methods(["GET"])
def manage_members_list(request):
    """View untuk staff melihat daftar member"""
    search_query = request.GET.get('search', '')
    members_queryset = Member.objects.all().select_related('user')
    
    if search_query:
        members_queryset = members_queryset.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(member_id__icontains=search_query)
        )
    
    paginator = Paginator(members_queryset, 10)
    page_number = request.GET.get('page', 1)
    members = paginator.get_page(page_number)
    
    context = {
        'members': members,
        'search_query': search_query,
    }
    return render(request, 'staff/manage_members.html', context)


@staff_required
@require_http_methods(["GET", "POST"])
def add_member(request):
    """View untuk staff menambahkan member baru"""
    if request.method == 'POST':
        form = AddMemberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Member baru berhasil ditambahkan!')
            return redirect('auth_system:manage_members_list')
        else:
            messages.error(request, 'Ada kesalahan saat menambahkan member.')
    else:
        form = AddMemberForm()
    
    context = {
        'form': form,
        'page_title': 'Tambah Member Baru',
    }
    return render(request, 'staff/add_member.html', context)


@staff_required
@require_http_methods(["GET", "POST"])
def edit_member(request, member_id):
    """View untuk staff mengedit data member"""
    try:
        member = Member.objects.get(member_id=member_id)
    except Member.DoesNotExist:
        messages.error(request, 'Member tidak ditemukan.')
        return redirect('auth_system:manage_members_list')
    
    if request.method == 'POST':
        form = EditMemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data member berhasil diperbarui!')
            return redirect('auth_system:manage_members_list')
        else:
            messages.error(request, 'Ada kesalahan saat memperbarui data member.')
    else:
        form = EditMemberForm(instance=member)
    
    context = {
        'form': form,
        'member': member,
        'page_title': 'Edit Data Member',
    }
    return render(request, 'staff/edit_member.html', context)


@staff_required
@require_http_methods(["POST"])
def delete_member(request, member_id):
    """View untuk staff menghapus member"""
    try:
        member = Member.objects.get(member_id=member_id)
        user = member.user
        member.delete()
        user.delete()
        messages.success(request, 'Member berhasil dihapus!')
    except Member.DoesNotExist:
        messages.error(request, 'Member tidak ditemukan.')
    
    return redirect('auth_system:manage_members_list')


# Member Identity CRUD Views

@member_required
@require_http_methods(["GET"])
def member_identities_list(request):
    """View untuk member melihat daftar identitas miliknya"""
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        messages.error(request, 'Profil member tidak ditemukan.')
        return redirect('auth_system:dashboard')
    
    identities = member.identities.all().order_by('-created_at')
    
    # Calculate status based on expiry date
    today = date.today()
    for identity in identities:
        if identity.expiry_date < today:
            identity.status = 'expired'
            identity.save()
    
    context = {
        'member': member,
        'identities': identities,
    }
    return render(request, 'member/identities_list.html', context)


@member_required
@require_http_methods(["GET", "POST"])
def add_member_identity(request):
    """View untuk member menambahkan dokumen identitas baru"""
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        messages.error(request, 'Profil member tidak ditemukan.')
        return redirect('auth_system:dashboard')
    
    if request.method == 'POST':
        form = AddIdentityForm(request.POST)
        if form.is_valid():
            identity = form.save(commit=False)
            identity.member = member
            
            # Validate dates
            if identity.issue_date > identity.expiry_date:
                messages.error(request, 'Tanggal terbit harus lebih awal dari tanggal habis.')
            else:
                identity.save()
                messages.success(request, 'Dokumen identitas berhasil ditambahkan!')
                return redirect('auth_system:member_identities_list')
        else:
            messages.error(request, 'Ada kesalahan saat menambahkan identitas.')
    else:
        form = AddIdentityForm()
    
    context = {
        'form': form,
        'member': member,
    }
    return render(request, 'member/add_identity.html', context)



@member_required
@require_http_methods(["GET", "POST"])
def edit_member_identity(request, identity_id):
    """View untuk member mengedit dokumen identitas"""
    try:
        member = Member.objects.get(user=request.user)
        identity = Identity.objects.get(id=identity_id, member=member)
    except (Member.DoesNotExist, Identity.DoesNotExist):
        messages.error(request, 'Dokumen identitas tidak ditemukan.')
        return redirect('auth_system:member_identities_list')
    
    if request.method == 'POST':
        form = EditIdentityForm(request.POST, instance=identity)
        if form.is_valid():
            identity = form.save(commit=False)
            
            # Validate dates
            if identity.issue_date > identity.expiry_date:
                messages.error(request, 'Tanggal terbit harus lebih awal dari tanggal habis.')
            else:
                identity.save()
                messages.success(request, 'Dokumen identitas berhasil diperbarui!')
                return redirect('auth_system:member_identities_list')
        else:
            messages.error(request, 'Ada kesalahan saat memperbarui identitas.')
    else:
        form = EditIdentityForm(instance=identity)
    
    context = {
        'form': form,
        'identity': identity,
        'member': member,
    }
    return render(request, 'member/edit_identity.html', context)



@member_required
@require_http_methods(["POST"])
def delete_member_identity(request, identity_id):
    """View untuk member menghapus dokumen identitas"""
    try:
        member = Member.objects.get(user=request.user)
        identity = Identity.objects.get(id=identity_id, member=member)
        identity.delete()
        messages.success(request, 'Dokumen identitas berhasil dihapus!')
    except (Member.DoesNotExist, Identity.DoesNotExist):
        messages.error(request, 'Dokumen identitas tidak ditemukan.')
    
    return redirect('auth_system:member_identities_list')
