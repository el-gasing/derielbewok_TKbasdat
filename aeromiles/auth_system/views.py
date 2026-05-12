from django.db import DatabaseError, connection, transaction
from django.db.models import F, Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from datetime import date
from .forms import (
    ClaimMissingMilesForm,
    IdentityForm,
    LoginForm,
    MemberRegistrationForm,
    MemberProfileSettingsForm,
    StaffClaimUpdateForm,
    StaffProfileSettingsForm,
    StaffRegistrationForm,
    StaffManageMemberCreateForm,
    StaffManageMemberUpdateForm,
    StyledPasswordChangeForm,
    TransferMilesForm,
    HadiahForm,
    _ensure_default_penyedia,
    _ensure_default_mitra,
)
from .models import ClaimMissingMiles, Hadiah, Identity, Maskapai, Member, Mitra, Penyedia, Staff, TransferMiles
from .services import check_duplicate_claim, update_member_tier


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


def _extract_db_error_message(exc):
    raw = str(exc).strip()
    if not raw:
        return 'Terjadi kesalahan saat memproses data di database.'

    # PostgreSQL exceptions often include prefixes like "ERROR:" and extra details.
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    for line in lines:
        if 'ERROR:' in line.upper():
            return line.split('ERROR:', 1)[-1].strip() if 'ERROR:' in line else line
    return lines[0]


def _reward_catalog():
    return [
        {
            'code': 'RWD-005',
            'name': 'Upgrade Business Class',
            'provider': 'Garuda Indonesia',
            'miles': 15000,
            'description': 'Upgrade dari economy class ke business class untuk rute domestik pilihan.',
            'valid_from': date(2026, 1, 1),
            'valid_until': date(2027, 1, 1),
            'category': 'Flight',
        },
        {
            'code': 'RWD-011',
            'name': 'Akses Lounge 1x',
            'provider': 'AeroMiles Lounge',
            'miles': 3000,
            'description': 'Akses satu kali ke lounge bandara partner sebelum penerbangan.',
            'valid_from': date(2026, 2, 1),
            'valid_until': date(2026, 12, 31),
            'category': 'Airport',
        },
        {
            'code': 'RWD-018',
            'name': 'Voucher Hotel Partner',
            'provider': 'AeroStay',
            'miles': 22000,
            'description': 'Potongan menginap untuk hotel partner AeroMiles di kota besar Indonesia.',
            'valid_from': date(2026, 3, 1),
            'valid_until': date(2026, 11, 30),
            'category': 'Travel',
        },
        {
            'code': 'RWD-002',
            'name': 'Extra Baggage 10 Kg',
            'provider': 'AeroMiles',
            'miles': 5000,
            'description': 'Tambahan bagasi 10 kg untuk penerbangan domestik tertentu.',
            'valid_from': date(2025, 1, 1),
            'valid_until': date(2025, 12, 31),
            'category': 'Flight',
        },
    ]


@login_required(login_url='auth_system:login')
def manage_members_list_view(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staf.')
        return redirect('auth_system:dashboard')

    search_query = request.GET.get('search', '').strip()
    members_qs = Member.objects.select_related('user').order_by('-created_at')
    if search_query:
        members_qs = members_qs.filter(
            Q(member_id__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
        )

    paginator = Paginator(members_qs, 10)
    members = paginator.get_page(request.GET.get('page'))
    return render(
        request,
        'staff/manage_member/manage_members.html',
        {'members': members, 'search_query': search_query, 'staff': staff},
    )


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def add_member_view(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staf.')
        return redirect('auth_system:dashboard')

    if request.method == 'POST':
        form = StaffManageMemberCreateForm(request.POST)
        if form.is_valid():
            _, member = form.save()
            messages.success(request, f'Member {member.member_id} berhasil ditambahkan.')
            return redirect('auth_system:manage_members_list')
    else:
        form = StaffManageMemberCreateForm()

    return render(request, 'staff/manage_member/add_member.html', {'form': form, 'staff': staff})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def edit_member_view(request, member_id):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staf.')
        return redirect('auth_system:dashboard')

    member = get_object_or_404(Member.objects.select_related('user'), member_id=member_id)
    if request.method == 'POST':
        form = StaffManageMemberUpdateForm(request.POST, member=member)
        if form.is_valid():
            form.save()
            messages.success(request, f'Data member {member.member_id} berhasil diperbarui.')
            return redirect('auth_system:manage_members_list')
    else:
        form = StaffManageMemberUpdateForm(member=member)

    return render(
        request,
        'staff/manage_member/edit_member.html',
        {'form': form, 'member': member, 'staff': staff},
    )


@require_http_methods(["POST"])
@login_required(login_url='auth_system:login')
def delete_member_view(request, member_id):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staf.')
        return redirect('auth_system:dashboard')

    member = get_object_or_404(Member.objects.select_related('user'), member_id=member_id)
    user = member.user
    deleted_member_id = member.member_id
    user.delete()
    messages.success(request, f'Member {deleted_member_id} berhasil dihapus.')
    return redirect('auth_system:manage_members_list')


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
@login_required(login_url='auth_system:login')
def profile_settings_view(request):
    user = request.user
    member = _get_member(user)
    staff = _get_staff(user)

    if member:
        profile = member
        user_type = 'member'
        profile_form_class = MemberProfileSettingsForm
    elif staff:
        profile = staff
        user_type = 'staff'
        profile_form_class = StaffProfileSettingsForm
    else:
        messages.error(request, 'Profil pengguna tidak ditemukan.')
        return redirect('auth_system:dashboard')

    profile_form = profile_form_class(user=user, profile=profile)
    password_form = StyledPasswordChangeForm(user=user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_profile':
            profile_form = profile_form_class(request.POST, user=user, profile=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profil berhasil diperbarui.')
                return redirect('auth_system:profile_settings')
            messages.error(request, 'Perubahan profil belum bisa disimpan. Periksa kembali input Anda.')

        elif action == 'change_password':
            password_form = StyledPasswordChangeForm(user=user, data=request.POST)
            profile_form = profile_form_class(user=user, profile=profile)
            if password_form.is_valid():
                updated_user = password_form.save()
                update_session_auth_hash(request, updated_user)
                messages.success(request, 'Password berhasil diperbarui.')
                return redirect('auth_system:profile_settings')
            messages.error(request, 'Password belum bisa diperbarui. Periksa kembali input Anda.')

    context = {
        'user_type': user_type,
        'member': member,
        'staff': staff,
        'profile_form': profile_form,
        'password_form': password_form,
    }
    return render(request, 'auth_system/profile_settings.html', context)


@login_required(login_url='auth_system:login')
def profile_view(request):
    return profile_settings_view(request)


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
            flight_number = form.cleaned_data.get('flight_number')
            ticket_number = form.cleaned_data.get('ticket_number')
            flight_date = form.cleaned_data.get('flight_date')

            duplicate_claim = check_duplicate_claim(
                member=member,
                flight_number=flight_number,
                ticket_number=ticket_number,
                flight_date=flight_date,
            )
            if duplicate_claim:
                messages.error(
                    request,
                    f'ERROR: Klaim untuk penerbangan "{flight_number}" pada tanggal "{flight_date}" dengan nomor tiket "{ticket_number}" sudah pernah diajukan sebelumnya.'
                )
                return render(request, 'auth_system/member_claim_form.html', {'form': form, 'title': 'Buat Claim Missing Miles'})

            claim = form.save(commit=False)
            claim.member = member
            claim.claim_id = _next_claim_id()
            claim.status = 'pending'
            try:
                with transaction.atomic():
                    claim.save()
                messages.success(request, f'Claim berhasil dibuat dengan ID {claim.claim_id}.')
                return redirect('auth_system:member_claim_list')
            except DatabaseError as exc:
                messages.error(request, _extract_db_error_message(exc))
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
            flight_number = form.cleaned_data.get('flight_number')
            ticket_number = form.cleaned_data.get('ticket_number')
            flight_date = form.cleaned_data.get('flight_date')

            duplicate_claim = check_duplicate_claim(
                member=member,
                flight_number=flight_number,
                ticket_number=ticket_number,
                flight_date=flight_date,
                exclude_claim_id=claim.id,
            )
            if duplicate_claim:
                messages.error(
                    request,
                    f'ERROR: Klaim untuk penerbangan "{flight_number}" pada tanggal "{flight_date}" dengan nomor tiket "{ticket_number}" sudah pernah diajukan sebelumnya.'
                )
                return render(request, 'auth_system/member_claim_form.html', {'form': form, 'title': f'Ubah Claim {claim.claim_id}'})

            try:
                with transaction.atomic():
                    form.save()
                messages.success(request, 'Claim berhasil diperbarui.')
                return redirect('auth_system:member_claim_list')
            except DatabaseError as exc:
                messages.error(request, _extract_db_error_message(exc))
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
            old_tier_name = updated_claim.member.tier.get_tier_name_display() if updated_claim.member.tier else 'None'

            try:
                with transaction.atomic():
                    updated_claim.save()

                    # Jika disetujui, akumulasi miles pada member.
                    if old_status != 'approved' and updated_claim.status == 'approved':
                        member = updated_claim.member
                        member.total_miles += updated_claim.miles_amount
                        member.save(update_fields=['total_miles'])

                        # Gunakan stored procedure pada PostgreSQL; fallback lokal untuk SQLite.
                        if connection.vendor == 'postgresql':
                            with connection.cursor() as cursor:
                                cursor.execute('SELECT sp_auto_update_member_tier(%s);', [member.id])
                            member.refresh_from_db(fields=['tier'])
                        else:
                            update_member_tier(member)

                        new_tier_name = member.tier.get_tier_name_display() if member.tier else 'None'
                        if old_tier_name != new_tier_name:
                            messages.success(
                                request,
                                f'SUKSES: Tier Member "{member.user.email}" telah diperbarui dari "{old_tier_name}" menjadi "{new_tier_name}" berdasarkan total miles yang dimiliki.'
                            )
                        else:
                            messages.success(
                                request,
                                f'Claim {updated_claim.claim_id} disetujui. Miles sebesar {updated_claim.miles_amount:,} telah ditambahkan ke member.'
                            )
                    else:
                        messages.success(request, f'Claim {updated_claim.claim_id} berhasil diperbarui.')

                return redirect('auth_system:staff_claim_list')
            except DatabaseError as exc:
                messages.error(request, _extract_db_error_message(exc))
    else:
        form = StaffClaimUpdateForm(instance=claim)

    return render(request, 'auth_system/staff_claim_form.html', {'form': form, 'claim': claim})


@login_required(login_url='auth_system:login')
@require_http_methods(["GET"])
def staff_transaction_report_view(request):
    summary = {
        'total_miles': '27,500',
        'monthly_redeem': '3,000',
        'approved_claims': '2,500',
    }
    transactions = [
        {
            'type': 'Transfer',
            'icon': 'fa-right-left',
            'member': 'John W. Doe',
            'email': 'john@example.com',
            'miles': '-5,000',
            'is_positive': False,
            'timestamp': '2025-01-15 10:30',
            'can_delete': True,
        },
        {
            'type': 'Redeem',
            'icon': 'fa-gift',
            'member': 'John W. Doe',
            'email': 'john@example.com',
            'miles': '-3,000',
            'is_positive': False,
            'timestamp': '2025-01-20 16:00',
            'can_delete': True,
        },
        {
            'type': 'Package',
            'icon': 'fa-cart-shopping',
            'member': 'Jane Smith',
            'email': 'jane@example.com',
            'miles': '+5,000',
            'is_positive': True,
            'timestamp': '2025-02-01 09:15',
            'can_delete': True,
        },
        {
            'type': 'Klaim',
            'icon': 'fa-plane',
            'member': 'Budi A. Santoso',
            'email': 'budi@example.com',
            'miles': '+2,500',
            'is_positive': True,
            'timestamp': '2025-02-05 11:45',
            'can_delete': False,
        },
        {
            'type': 'Transfer',
            'icon': 'fa-right-left',
            'member': 'Budi A. Santoso',
            'email': 'budi@example.com',
            'miles': '-2,000',
            'is_positive': False,
            'timestamp': '2025-02-10 14:00',
            'can_delete': True,
        },
        {
            'type': 'Package',
            'icon': 'fa-cart-shopping',
            'member': 'John W. Doe',
            'email': 'john@example.com',
            'miles': '+10,000',
            'is_positive': True,
            'timestamp': '2025-03-01 08:00',
            'can_delete': True,
        },
    ]
    top_members = [
        {
            'rank': 1,
            'name': 'John W. Doe',
            'email': 'john@example.com',
            'total_miles': '18,000',
            'transactions': 3,
        },
        {
            'rank': 2,
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'total_miles': '5,000',
            'transactions': 1,
        },
        {
            'rank': 3,
            'name': 'Budi A. Santoso',
            'email': 'budi@example.com',
            'total_miles': '4,500',
            'transactions': 2,
        },
    ]

    context = {
        'summary': summary,
        'transactions': transactions,
        'top_members': top_members,
    }
    return render(request, 'staff/report/staff_transaction_report.html', context)


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


@login_required(login_url='auth_system:login')
def member_redeem_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    rewards = _reward_catalog()
    available_rewards = [
        reward for reward in rewards
        if reward['valid_until'] >= date.today()
    ]

    redeem_history = [
        {
            'reward': 'Akses Lounge 1x',
            'timestamp': '2025-01-20 16:00',
            'miles': 3000,
            'status': 'Selesai',
        },
        {
            'reward': 'Extra Baggage 10 Kg',
            'timestamp': '2024-12-08 09:30',
            'miles': 5000,
            'status': 'Selesai',
        },
    ]

    context = {
        'member': member,
        'rewards': available_rewards,
        'redeem_history': redeem_history,
    }
    return render(request, 'member/redeem/member_redeem.html', context)


@login_required(login_url='auth_system:login')
def staff_rewards_view(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    rewards = _reward_catalog()
    context = {
        'staff': staff,
        'rewards': rewards,
        'active_rewards': [reward for reward in rewards if reward['valid_until'] >= date.today()],
        'maskapai_list': Maskapai.objects.filter(is_active=True).order_by('name'),
        'penyedia_list': Penyedia.objects.filter(is_active=True).order_by('name'),
    }
    return render(request, 'staff/reward/staff_rewards.html', context)


@login_required(login_url='auth_system:login')
def staff_partners_view(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    context = {
        'staff': staff,
        'partners': Mitra.objects.order_by('-is_active', 'name'),
    }
    return render(request, 'staff/partner/staff_partners.html', context)


@login_required(login_url='auth_system:login')
def member_package_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    packages = [
        {
            'code': 'AMP-001',
            'miles': 1000,
            'price': 150000,
            'label': 'Starter',
        },
        {
            'code': 'AMP-002',
            'miles': 5000,
            'price': 650000,
            'label': 'Traveler',
        },
        {
            'code': 'AMP-003',
            'miles': 10000,
            'price': 1200000,
            'label': 'Explorer',
        },
        {
            'code': 'AMP-004',
            'miles': 25000,
            'price': 2750000,
            'label': 'Priority',
        },
    ]

    context = {
        'member': member,
        'packages': packages,
    }
    return render(request, 'member/package/member_package.html', context)


@login_required(login_url='auth_system:login')
def member_tier_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    tiers = [
        {
            'code': 'blue',
            'name': 'Blue',
            'flight_min': 0,
            'miles_min': 0,
            'color': '#2f9bd7',
            'benefits': [
                'Akumulasi miles dasar',
                'Akses penawaran khusus member',
            ],
        },
        {
            'code': 'silver',
            'name': 'Silver',
            'flight_min': 10,
            'miles_min': 15000,
            'color': '#8b98a8',
            'benefits': [
                'Bonus miles 25%',
                'Priority check-in',
                'Akses lounge partner',
            ],
        },
        {
            'code': 'gold',
            'name': 'Gold',
            'flight_min': 25,
            'miles_min': 40000,
            'color': '#d4a72c',
            'benefits': [
                'Bonus miles 50%',
                'Priority boarding',
                'Akses lounge premium',
                'Extra bagasi 10kg',
            ],
        },
        {
            'code': 'platinum',
            'name': 'Platinum',
            'flight_min': 50,
            'miles_min': 80000,
            'color': '#111827',
            'benefits': [
                'Bonus miles 100%',
                'Upgrade gratis sesuai ketersediaan',
                'Akses lounge first class',
                'Extra bagasi 20kg',
                'Dedicated hotline',
            ],
        },
    ]

    current_tier = tiers[0]
    for tier in tiers:
        if member.total_miles >= tier['miles_min']:
            current_tier = tier

    current_index = tiers.index(current_tier)
    next_tier = tiers[current_index + 1] if current_index + 1 < len(tiers) else None
    if next_tier:
        progress_start = current_tier['miles_min']
        progress_target = next_tier['miles_min']
        progress_range = progress_target - progress_start
        progress_value = max(0, member.total_miles - progress_start)
        progress_percent = min(100, int((progress_value / progress_range) * 100)) if progress_range else 100
    else:
        progress_target = current_tier['miles_min']
        progress_percent = 100

    context = {
        'member': member,
        'tiers': tiers,
        'current_tier': current_tier,
        'next_tier': next_tier,
        'progress_target': progress_target,
        'progress_percent': progress_percent,
    }
    return render(request, 'member/tier/member_tier.html', context)


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


@login_required(login_url='auth_system:login')
def member_identities_list_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    identities = Identity.objects.filter(member=member).order_by('-created_at')
    return render(request, 'member/identity/identities_list.html', {'member': member, 'identities': identities})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def add_member_identity_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    if request.method == 'POST':
        form = IdentityForm(request.POST)
        if form.is_valid():
            identity = form.save(commit=False)
            identity.member = member
            identity.is_expired = identity.expiry_date <= date.today()
            identity.save()
            messages.success(request, 'Identitas berhasil ditambahkan.')
            return redirect('auth_system:member_identities_list')
    else:
        form = IdentityForm()

    return render(request, 'member/identity/add_identity.html', {'form': form})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def edit_member_identity_view(request, identity_id):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    identity = get_object_or_404(Identity, id=identity_id, member=member)
    if request.method == 'POST':
        form = IdentityForm(request.POST, instance=identity)
        if form.is_valid():
            updated_identity = form.save(commit=False)
            updated_identity.member = member
            updated_identity.is_expired = updated_identity.expiry_date <= date.today()
            updated_identity.save()
            messages.success(request, 'Identitas berhasil diperbarui.')
            return redirect('auth_system:member_identities_list')
    else:
        form = IdentityForm(instance=identity)
        form.fields['document_number'].widget.attrs['readonly'] = True

    return render(request, 'member/identity/edit_identity.html', {'form': form})


@require_http_methods(["POST"])
@login_required(login_url='auth_system:login')
def delete_member_identity_view(request, identity_id):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    identity = get_object_or_404(Identity, id=identity_id, member=member)
    identity.delete()
    messages.success(request, 'Identitas berhasil dihapus.')
    return redirect('auth_system:member_identities_list')


# ===================== VIEWS UNTUK MANAJEMEN HADIAH (STAFF) =====================

@login_required(login_url='auth_system:login')
def staff_hadiah_list_view(request):
    """View untuk melihat daftar hadiah (staff)"""
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staf.')
        return redirect('auth_system:dashboard')

    _ensure_default_penyedia()
    _ensure_default_mitra()

    # Filter berdasarkan parameter query
    hadiah_list = Hadiah.objects.select_related('penyedia', 'mitra').all().order_by('-created_at')

    # Filter berdasarkan penyedia
    penyedia_id = request.GET.get('penyedia', '')
    if penyedia_id:
        hadiah_list = hadiah_list.filter(penyedia_id=penyedia_id)

    # Filter berdasarkan status keaktifan
    status = request.GET.get('status', '')
    if status:
        hadiah_list = hadiah_list.filter(status=status)

    # Get semua penyedia aktif untuk dropdown filter
    penyedia_list = Penyedia.objects.filter(is_active=True).values_list('id', 'name').order_by('name')

    context = {
        'hadiah_list': hadiah_list,
        'penyedia_list': penyedia_list,
        'selected_penyedia': penyedia_id,
        'selected_status': status,
        'staff': staff,
    }
    return render(request, 'staff/hadiah/hadiah_list.html', context)


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def staff_hadiah_create_view(request):
    """View untuk membuat hadiah baru (staff)"""
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staf.')
        return redirect('auth_system:dashboard')

    _ensure_default_penyedia()
    _ensure_default_mitra()

    if request.method == 'POST':
        form = HadiahForm(request.POST)
        if form.is_valid():
            hadiah = form.save()
            messages.success(request, f'Hadiah "{hadiah.nama_hadiah}" berhasil ditambahkan.')
            return redirect('auth_system:staff_hadiah_list')
    else:
        form = HadiahForm()

    context = {
        'form': form,
        'staff': staff,
        'title': 'Tambah Hadiah Baru',
    }
    return render(request, 'staff/hadiah/hadiah_form.html', context)


@login_required(login_url='auth_system:login')
def staff_hadiah_detail_view(request, hadiah_id):
    """View untuk melihat detail hadiah (staff)"""
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staf.')
        return redirect('auth_system:dashboard')

    hadiah = get_object_or_404(Hadiah.objects.select_related('penyedia', 'mitra'), id=hadiah_id)

    context = {
        'hadiah': hadiah,
        'staff': staff,
    }
    return render(request, 'staff/hadiah/hadiah_detail.html', context)


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def staff_hadiah_update_view(request, hadiah_id):
    """View untuk mengedit hadiah (staff)"""
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staf.')
        return redirect('auth_system:dashboard')

    hadiah = get_object_or_404(Hadiah.objects.select_related('penyedia', 'mitra'), id=hadiah_id)

    if request.method == 'POST':
        form = HadiahForm(request.POST, instance=hadiah)
        if form.is_valid():
            updated_hadiah = form.save()
            messages.success(request, f'Hadiah "{updated_hadiah.nama_hadiah}" berhasil diperbarui.')
            return redirect('auth_system:staff_hadiah_detail', hadiah_id=hadiah.id)
    else:
        form = HadiahForm(instance=hadiah)

    context = {
        'form': form,
        'hadiah': hadiah,
        'staff': staff,
        'title': 'Edit Hadiah',
    }
    return render(request, 'staff/hadiah/hadiah_form.html', context)


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def staff_hadiah_delete_view(request, hadiah_id):
    """View untuk menghapus hadiah (staff)"""
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staf.')
        return redirect('auth_system:dashboard')

    hadiah = get_object_or_404(Hadiah.objects.select_related('penyedia', 'mitra'), id=hadiah_id)
    nama_hadiah = hadiah.nama_hadiah

    if not hadiah.sudah_kadaluarsa:
        messages.error(request, 'Hadiah hanya dapat dihapus jika periode validitasnya sudah selesai.')
        return redirect('auth_system:staff_hadiah_detail', hadiah_id=hadiah.id)

    if request.method == 'POST':
        hadiah.delete()
        messages.success(request, f'Hadiah "{nama_hadiah}" berhasil dihapus.')
        return redirect('auth_system:staff_hadiah_list')

    context = {
        'hadiah': hadiah,
        'staff': staff,
    }
    return render(request, 'staff/hadiah/hadiah_confirm_delete.html', context)
