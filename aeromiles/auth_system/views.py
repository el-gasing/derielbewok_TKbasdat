from django.db import transaction
from django.db.models import F, Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from datetime import date
from .forms import (
    ClaimMissingMilesForm,
    IdentityForm,
    LoginForm,
    MemberRegistrationForm,
    StaffClaimUpdateForm,
    StaffMemberCreateForm,
    StaffMemberUpdateForm,
    StaffRegistrationForm,
    TransferMilesForm,
)
from .models import ClaimMissingMiles, Identity, Maskapai, Member, Mitra, Penyedia, Staff, TransferMiles


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
    old_status = claim.status
    
    if request.method == 'POST':
        form = StaffClaimUpdateForm(request.POST, instance=claim)
        if form.is_valid():
            updated_claim = form.save(commit=False)
            updated_claim.approved_by = staff
            updated_claim.save()
            
            # Nambah total_miles member jika status berubah menjadi 'approved'
            if old_status != 'approved' and updated_claim.status == 'approved':
                member = updated_claim.member
                member.total_miles += updated_claim.miles_amount
                member.save()
                messages.success(request, f'Claim {updated_claim.claim_id} berhasil disetujui. Miles sebesar {updated_claim.miles_amount:,} telah ditambahkan ke member.')
            else:
                messages.success(request, f'Claim {updated_claim.claim_id} berhasil diperbarui.')
            
            return redirect('auth_system:staff_claim_list')
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
def manage_members_list(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    search_query = request.GET.get('search', '').strip()
    members = Member.objects.select_related('user').order_by('member_id')

    if search_query:
        members = members.filter(
            Q(member_id__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    paginator = Paginator(members, 10)
    members_page = paginator.get_page(request.GET.get('page'))

    return render(request, 'staff/manage_member/manage_members.html', {
        'staff': staff,
        'members': members_page,
        'search_query': search_query,
    })


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def add_member(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    if request.method == 'POST':
        form = StaffMemberCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Member baru berhasil ditambahkan.')
            return redirect('auth_system:manage_members_list')
    else:
        form = StaffMemberCreateForm()

    return render(request, 'staff/manage_member/add_member.html', {'form': form})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def edit_member(request, member_id):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    member = get_object_or_404(Member, member_id=member_id)

    if request.method == 'POST':
        form = StaffMemberUpdateForm(request.POST, member=member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data member berhasil diperbarui.')
            return redirect('auth_system:manage_members_list')
    else:
        form = StaffMemberUpdateForm(
            initial={
                'email': member.user.email,
                'first_name': member.user.first_name,
                'last_name': member.user.last_name,
                'phone_number': member.phone_number,
            },
            member=member,
        )

    return render(request, 'staff/manage_member/edit_member.html', {'form': form, 'member': member})


@require_http_methods(["POST"])
@login_required(login_url='auth_system:login')
def delete_member(request, member_id):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    member = get_object_or_404(Member, member_id=member_id)
    member.user.delete()
    messages.success(request, f'Member {member.member_id} berhasil dihapus.')
    return redirect('auth_system:manage_members_list')


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
def profile_view(request):
    member = _get_member(request.user)
    staff = _get_staff(request.user)

    if not member and not staff:
        messages.error(request, 'Profil hanya tersedia untuk member atau staff.')
        return redirect('auth_system:dashboard')

    context = {
        'member': member,
        'staff': staff,
        'profile_type': 'member' if member else 'staff',
    }
    return render(request, 'auth_system/profile.html', context)


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