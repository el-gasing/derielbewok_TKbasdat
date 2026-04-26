from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .forms import (
    ClaimMissingMilesForm,
    LoginForm,
    MemberRegistrationForm,
    StaffClaimUpdateForm,
    StaffRegistrationForm,
    TransferMilesForm,
)
from .models import ClaimMissingMiles, Member, Staff, TransferMiles


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
    
    return render(request, 'auth_system/login.html', {'form': form})


@require_http_methods(["POST"])
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
    member = _get_member(user)
    if member:
        context['user_type'] = 'member'
        context['member'] = member
    
    # Check if user is staff
    staff = _get_staff(user)
    if staff:
        context['user_type'] = 'staff'
        context['staff'] = staff
    
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


@login_required(login_url='auth_system:login')
def member_claim_list_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    claims = ClaimMissingMiles.objects.filter(member=member).order_by('-created_at')
    return render(request, 'auth_system/member_claim_list.html', {'member': member, 'claims': claims})


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

    return render(request, 'auth_system/member_claim_form.html', {'form': form, 'title': 'Buat Claim Missing Miles'})


@login_required(login_url='auth_system:login')
def member_claim_detail_view(request, claim_id):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    claim = get_object_or_404(ClaimMissingMiles, id=claim_id, member=member)
    return render(request, 'auth_system/member_claim_detail.html', {'claim': claim})


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

    return render(request, 'auth_system/member_claim_form.html', {'form': form, 'title': f'Ubah Claim {claim.claim_id}'})


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
    return render(request, 'auth_system/staff_claim_list.html', {'staff': staff, 'claims': claims})


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

    return render(request, 'auth_system/staff_claim_form.html', {'form': form, 'claim': claim})


@login_required(login_url='auth_system:login')
def member_transfer_list_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    transfers = TransferMiles.objects.filter(
        Q(from_member=member) | Q(to_member=member)
    ).select_related('from_member', 'from_member__user', 'to_member', 'to_member__user').order_by('-created_at')
    return render(request, 'auth_system/member_transfer_list.html', {'member': member, 'transfers': transfers})


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

    return render(request, 'auth_system/member_transfer_form.html', {'form': form, 'member': member})
