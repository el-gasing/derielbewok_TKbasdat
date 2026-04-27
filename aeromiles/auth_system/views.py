from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import Http404
from django.core.paginator import Paginator
from django.db.models import Q
from functools import wraps
from datetime import date
from .forms import LoginForm, MemberRegistrationForm, StaffRegistrationForm, AddMemberForm, EditMemberForm, AddIdentityForm, EditIdentityForm, ClaimMissingMilesForm, MemberRegistrationForm, StaffClaimUpdateForm, TransferMilesForm
from .models import Member, Staff, Identity, ClaimMissingMiles, TransferMiles


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

def _next_claim_id():
    last_claim = ClaimMissingMiles.objects.order_by('id').last()
    if not last_claim:
        return 'CLM000001'
    last_num = int(last_claim.claim_id.replace('CLM', ''))
    return f'CLM{last_num + 1:06d}'


def _next_transfer_id():
    last_transfer = TransferMiles.objects.order_by('id').last()
    if not last_transfer:
        return 'TRF000001'
    last_num = int(last_transfer.transfer_id.replace('TRF', ''))
    return f'TRF{last_num + 1:06d}'


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
    return render(request, 'staff/manage_member/manage_members.html', context)


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
    return render(request, 'staff/manage_member/edit_member.html', context)


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
    return render(request, 'member/identity/identities_list.html', context)


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
    return render(request, 'member/identity/add_identity.html', context)



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
    return render(request, 'member/identity/edit_identity.html', context)


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

@login_required(login_url='auth_system:login')
def member_claim_list_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    claims = ClaimMissingMiles.objects.filter(member=member).order_by('-created_at')
    return render(request, 'member/claim/member_claim_list.html', {'member': member, 'claims': claims})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def member_claim_create_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    if request.method == 'POST':
        form = ClaimMissingMilesForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.member = member
            claim.claim_id = _next_claim_id()
            claim.status = 'pending'
            claim.save()
            messages.success(request, f'Claim berhasil dibuat dengan ID {claim.claim_id}.')
            return redirect('auth_system:member_claim_list')
    else:
        form = ClaimMissingMilesForm()

    return render(request, 'member/claim/member_claim_form.html', {'form': form, 'title': 'Buat Claim Missing Miles'})


@login_required(login_url='auth_system:login')
def member_claim_detail_view(request, claim_id):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    claim = get_object_or_404(ClaimMissingMiles, id=claim_id, member=member)
    return render(request, 'member/claim/member_claim_detail.html', {'claim': claim})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def member_claim_update_view(request, claim_id):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    claim = get_object_or_404(ClaimMissingMiles, id=claim_id, member=member)
    if request.method == 'POST':
        form = ClaimMissingMilesForm(request.POST, instance=claim)
        if form.is_valid():
            form.save()
            messages.success(request, 'Claim berhasil diperbarui.')
            return redirect('auth_system:member_claim_list')
    else:
        form = ClaimMissingMilesForm(instance=claim)

    return render(request, 'member/claim/member_claim_form.html', {'form': form, 'title': f'Ubah Claim {claim.claim_id}'})


@require_http_methods(["POST"])
@login_required(login_url='auth_system:login')
def member_claim_delete_view(request, claim_id):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    claim = get_object_or_404(ClaimMissingMiles, id=claim_id, member=member)
    claim_id_value = claim.claim_id
    claim.delete()
    messages.success(request, f'Claim {claim_id_value} berhasil dihapus.')
    return redirect('auth_system:member_claim_list')


@login_required(login_url='auth_system:login')
def staff_claim_list_view(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    claims = ClaimMissingMiles.objects.select_related('member', 'member__user').order_by('-created_at')
    return render(request, 'staff/claim/staff_claim_list.html', {'staff': staff, 'claims': claims})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def staff_claim_update_view(request, claim_id):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    claim = get_object_or_404(ClaimMissingMiles, id=claim_id)
    if request.method == 'POST':
        form = StaffClaimUpdateForm(request.POST, instance=claim)
        if form.is_valid():
            updated_claim = form.save(commit=False)
            updated_claim.approved_by = staff
            updated_claim.save()
            messages.success(request, f'Claim {updated_claim.claim_id} berhasil diperbarui.')
            return redirect('auth_system:staff_claim_list')
    else:
        form = StaffClaimUpdateForm(instance=claim)

    return render(request, 'staff/claim/staff_claim_form.html', {'form': form, 'claim': claim})


@login_required(login_url='auth_system:login')
def member_transfer_list_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    transfers = TransferMiles.objects.filter(
        Q(from_member=member) | Q(to_member=member)
    ).select_related('from_member', 'from_member__user', 'to_member', 'to_member__user').order_by('-created_at')
    return render(request, 'member/transfer/member_transfer_list.html', {'member': member, 'transfers': transfers})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def member_transfer_create_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    if request.method == 'POST':
        form = TransferMilesForm(request.POST, from_member=member)
        if form.is_valid():
            with transaction.atomic():
                from_member = Member.objects.select_for_update().get(id=member.id)
                to_member = Member.objects.select_for_update().get(id=form.to_member.id)
                miles_amount = form.cleaned_data['miles_amount']

                if from_member.total_miles < miles_amount:
                    form.add_error('miles_amount', 'Total miles tidak mencukupi untuk transfer ini.')
                else:
                    transfer = TransferMiles.objects.create(
                        from_member=from_member,
                        to_member=to_member,
                        transfer_id=_next_transfer_id(),
                        miles_amount=miles_amount,
                        status='completed',
                        description=form.cleaned_data.get('description', ''),
                    )

                    from_member.total_miles = F('total_miles') - miles_amount
                    to_member.total_miles = F('total_miles') + miles_amount
                    from_member.save(update_fields=['total_miles'])
                    to_member.save(update_fields=['total_miles'])
                    messages.success(request, f'Transfer berhasil dengan ID {transfer.transfer_id}.')
                    return redirect('auth_system:member_transfer_list')
    else:
        form = TransferMilesForm(from_member=member)

    return render(request, 'member/transfer/member_transfer_form.html', {'form': form, 'member': member})

def _get_member(user):
    """Mengembalikan profil member atau None."""
    try:
        return Member.objects.get(user=user)
    except Member.DoesNotExist:
        return None


def _get_staff(user):
    """Mengembalikan profil staff atau None."""
    try:
        return Staff.objects.get(user=user)
    except Staff.DoesNotExist:
        return None