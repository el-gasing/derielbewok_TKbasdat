from types import SimpleNamespace
from django import forms
from django.db import DatabaseError, connection, transaction
from django.http import Http404
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from datetime import date


def _row_to_ns(cursor, row):
    if row is None:
        return None
    return SimpleNamespace(**dict(zip([c[0] for c in cursor.description], row)))


def _rows_to_ns(cursor, rows):
    cols = [c[0] for c in cursor.description]
    return [SimpleNamespace(**dict(zip(cols, r))) for r in rows]
from .forms import (
    ClaimMissingMilesForm,
    IdentityForm,
    LoginForm,
    MemberRegistrationForm,
    MemberProfileSettingsForm,
    MitraForm,
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
from .models import (
    AwardMilesPackage, Bandara, ClaimMissingMiles, Identity,
    Maskapai, Member, MemberAwardMilesPackage, Mitra,
    Redeem, Staff, TransferMiles,
)
from .services import check_duplicate_claim, update_member_tier


def _get_member(user):
    if user is None or not user.is_authenticated:
        return None
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT m.id, m.user_id, m.member_id, m.salutation, m.country_code,
                   m.phone_number, m.birth_date, m.nationality, m.tier_id,
                   m.total_miles, m.award_miles, m.is_active,
                   m.created_at, m.updated_at,
                   u.email, u.username, u.first_name, u.last_name,
                   t.tier_name, t.minimal_tier_miles
            FROM auth_system_member m
            JOIN auth_user u ON u.id = m.user_id
            LEFT JOIN auth_system_tier t ON t.id = m.tier_id
            WHERE m.user_id = %s
        """, [user.id])
        row = cursor.fetchone()
    if not row:
        return None
    return SimpleNamespace(
        id=row[0], user_id=row[1], member_id=row[2], salutation=row[3],
        country_code=row[4], phone_number=row[5], birth_date=row[6],
        nationality=row[7], tier_id=row[8], total_miles=row[9],
        award_miles=row[10], is_active=row[11], created_at=row[12],
        updated_at=row[13],
        user=SimpleNamespace(id=row[1], email=row[14], username=row[15],
                             first_name=row[16], last_name=row[17]),
        tier=SimpleNamespace(id=row[8], tier_name=row[18],
                             minimal_tier_miles=row[19]) if row[8] else None,
    )


_STATUS_LABELS = {
    'pending': 'Pending', 'approved': 'Approved',
    'rejected': 'Rejected', 'processed': 'Processed',
}
_KABIN_LABELS = {'economy': 'Economy', 'business': 'Business', 'first': 'First Class'}


def _build_claim_ns(d):
    ns = SimpleNamespace(
        id=d['id'], claim_id=d['claim_id'], flight_number=d['flight_number'],
        flight_date=d['flight_date'], ticket_number=d['ticket_number'],
        miles_amount=d['miles_amount'], status=d['status'], reason=d['reason'],
        description=d['description'], pnr=d['pnr'], kelas_kabin=d['kelas_kabin'],
        created_at=d['created_at'], updated_at=d['updated_at'],
        member_id_fk=d['member_id'], approved_by_id=d.get('approved_by_id'),
        get_status_display=lambda s=d['status']: _STATUS_LABELS.get(s, s),
        get_kelas_kabin_display=lambda k=d['kelas_kabin']: _KABIN_LABELS.get(k, '') if k else '',
    )
    ns.maskapai = SimpleNamespace(
        id=d.get('maskapai_id'), code=d.get('maskapai_code'),
        name=d.get('maskapai_name')
    ) if d.get('maskapai_id') else None
    ns.bandara_asal = SimpleNamespace(
        iata_code=d.get('asal_iata'), nama=d.get('asal_nama')
    ) if d.get('asal_iata') else None
    ns.bandara_tujuan = SimpleNamespace(
        iata_code=d.get('tujuan_iata'), nama=d.get('tujuan_nama')
    ) if d.get('tujuan_iata') else None
    if 'm_member_id' in d:
        ns.member = SimpleNamespace(
            id=d['member_id'], member_id=d['m_member_id'],
            total_miles=d.get('m_total_miles'),
            user=SimpleNamespace(username=d.get('u_username'),
                                 email=d.get('u_email')),
            tier=SimpleNamespace(tier_name=d.get('t_tier_name'),
                                 get_tier_name_display=lambda n=d.get('t_tier_name'):
                                     dict([('bronze','Bronze'),('silver','Silver'),
                                           ('gold','Gold'),('platinum','Platinum')]).get(n, n))
                  if d.get('t_tier_name') else None,
        )
    if 'approved_by_username' in d and d.get('approved_by_username'):
        ns.approved_by = SimpleNamespace(
            user=SimpleNamespace(username=d['approved_by_username'])
        )
    else:
        ns.approved_by = None
    return ns


_CLAIM_BASE_SELECT = """
    SELECT c.id, c.member_id, c.claim_id, c.flight_number, c.flight_date,
           c.ticket_number, c.miles_amount, c.status, c.reason, c.description,
           c.pnr, c.kelas_kabin, c.created_at, c.updated_at, c.approved_by_id,
           c.maskapai_id, mk.code AS maskapai_code, mk.name AS maskapai_name,
           ba.iata_code AS asal_iata, ba.nama AS asal_nama,
           bt.iata_code AS tujuan_iata, bt.nama AS tujuan_nama
    FROM auth_system_claimmissingmiles c
    LEFT JOIN auth_system_maskapai mk ON mk.id = c.maskapai_id
    LEFT JOIN auth_system_bandara ba ON ba.iata_code = c.bandara_asal_id
    LEFT JOIN auth_system_bandara bt ON bt.iata_code = c.bandara_tujuan_id
"""


def _get_mitra_by_id(mitra_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, code, contact_person, email, phone_number,
                   tanggal_kerja_sama, is_active, created_at, updated_at
            FROM auth_system_mitra WHERE id = %s
        """, [mitra_id])
        row = cursor.fetchone()
    if not row:
        return None
    return SimpleNamespace(
        id=row[0], name=row[1], code=row[2], contact_person=row[3],
        email=row[4], phone_number=row[5], tanggal_kerja_sama=row[6],
        is_active=row[7], created_at=row[8], updated_at=row[9],
    )


def _get_identity_by_id(identity_id, member_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, member_id, document_number, document_type, country,
                   issue_date, expiry_date, is_expired, created_at, updated_at
            FROM auth_system_identity
            WHERE id = %s AND member_id = %s
        """, [identity_id, member_id])
        row = cursor.fetchone()
    if not row:
        return None
    return SimpleNamespace(
        id=row[0], member_id=row[1], document_number=row[2],
        document_type=row[3], country=row[4], issue_date=row[5],
        expiry_date=row[6], is_expired=row[7], created_at=row[8],
        updated_at=row[9],
    )


def _get_hadiah_by_id(hadiah_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT h.id, h.kode_hadiah, h.nama_hadiah, h.deskripsi,
                   h.miles_diperlukan, h.tanggal_valid_mulai, h.tanggal_valid_akhir,
                   h.is_active, h.created_at, h.updated_at,
                   h.penyedia_id, h.mitra_id,
                   p.name AS p_name, p.code AS p_code,
                   mt.name AS mt_name, mt.code AS mt_code
            FROM auth_system_hadiah h
            LEFT JOIN auth_system_penyedia p ON p.id = h.penyedia_id
            LEFT JOIN auth_system_mitra mt ON mt.id = h.mitra_id
            WHERE h.id = %s
        """, [hadiah_id])
        cols = [c[0] for c in cursor.description]
        row = cursor.fetchone()
    if not row:
        return None
    d = dict(zip(cols, row))
    ns = SimpleNamespace(
        id=d['id'], kode_hadiah=d['kode_hadiah'], nama_hadiah=d['nama_hadiah'],
        deskripsi=d['deskripsi'], miles_diperlukan=d['miles_diperlukan'],
        tanggal_valid_mulai=d['tanggal_valid_mulai'],
        tanggal_valid_akhir=d['tanggal_valid_akhir'],
        is_active=d['is_active'], created_at=d['created_at'],
        updated_at=d['updated_at'],
        penyedia_id=d['penyedia_id'], mitra_id=d['mitra_id'],
    )
    ns.penyedia = SimpleNamespace(
        id=d['penyedia_id'], name=d['p_name'], code=d['p_code']
    ) if d['penyedia_id'] else None
    ns.mitra = SimpleNamespace(
        id=d['mitra_id'], name=d['mt_name'], code=d['mt_code']
    ) if d['mitra_id'] else None
    return ns


def _get_claim_by_id(claim_id, member_id=None):
    sql = """
        SELECT c.id, c.member_id, c.claim_id, c.flight_number, c.flight_date,
               c.ticket_number, c.miles_amount, c.status, c.reason, c.description,
               c.pnr, c.kelas_kabin, c.created_at, c.updated_at, c.approved_by_id,
               c.maskapai_id, c.bandara_asal_id, c.bandara_tujuan_id,
               mk.code AS maskapai_code, mk.name AS maskapai_name,
               ba.iata_code AS asal_iata, ba.nama AS asal_nama,
               bt.iata_code AS tujuan_iata, bt.nama AS tujuan_nama,
               m.member_id AS m_member_id, m.total_miles AS m_total_miles,
               u.username AS u_username, u.email AS u_email,
               t.tier_name AS t_tier_name,
               sa.username AS approved_by_username
        FROM auth_system_claimmissingmiles c
        JOIN auth_system_member m ON m.id = c.member_id
        JOIN auth_user u ON u.id = m.user_id
        LEFT JOIN auth_system_tier t ON t.id = m.tier_id
        LEFT JOIN auth_system_maskapai mk ON mk.id = c.maskapai_id
        LEFT JOIN auth_system_bandara ba ON ba.iata_code = c.bandara_asal_id
        LEFT JOIN auth_system_bandara bt ON bt.iata_code = c.bandara_tujuan_id
        LEFT JOIN auth_system_staff staf ON staf.id = c.approved_by_id
        LEFT JOIN auth_user sa ON sa.id = staf.user_id
        WHERE c.id = %s
    """
    params = [claim_id]
    if member_id is not None:
        sql += " AND c.member_id = %s"
        params.append(member_id)

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        cols = [x[0] for x in cursor.description]
        row = cursor.fetchone()
    if not row:
        return None
    d = dict(zip(cols, row))
    ns = _build_claim_ns(d)
    ns.maskapai_id = d.get('maskapai_id')
    ns.bandara_asal_id = d.get('bandara_asal_id')
    ns.bandara_tujuan_id = d.get('bandara_tujuan_id')
    return ns


def _get_member_by_id(member_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT m.id, m.user_id, m.member_id, m.salutation, m.country_code,
                   m.phone_number, m.birth_date, m.nationality, m.tier_id,
                   m.total_miles, m.award_miles, m.is_active,
                   m.created_at, m.updated_at,
                   u.email, u.username, u.first_name, u.last_name,
                   t.tier_name, t.minimal_tier_miles
            FROM auth_system_member m
            JOIN auth_user u ON u.id = m.user_id
            LEFT JOIN auth_system_tier t ON t.id = m.tier_id
            WHERE m.member_id = %s
        """, [member_id])
        row = cursor.fetchone()
    if not row:
        return None
    return SimpleNamespace(
        id=row[0], user_id=row[1], member_id=row[2], salutation=row[3],
        country_code=row[4], phone_number=row[5], birth_date=row[6],
        nationality=row[7], tier_id=row[8], total_miles=row[9],
        award_miles=row[10], is_active=row[11], created_at=row[12],
        updated_at=row[13],
        user=SimpleNamespace(id=row[1], pk=row[1], email=row[14], username=row[15],
                             first_name=row[16], last_name=row[17]),
        tier=SimpleNamespace(id=row[8], tier_name=row[18],
                             minimal_tier_miles=row[19]) if row[8] else None,
    )


def _get_staff(user):
    if user is None or not user.is_authenticated:
        return None
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT s.id, s.user_id, s.staff_id, s.salutation, s.country_code,
                   s.phone_number, s.birth_date, s.nationality, s.maskapai_id,
                   s.department, s.is_active, s.created_at, s.updated_at,
                   u.email, u.username, u.first_name, u.last_name
            FROM auth_system_staff s
            JOIN auth_user u ON u.id = s.user_id
            WHERE s.user_id = %s
        """, [user.id])
        row = cursor.fetchone()
    if not row:
        return None
    return SimpleNamespace(
        id=row[0], user_id=row[1], staff_id=row[2], salutation=row[3],
        country_code=row[4], phone_number=row[5], birth_date=row[6],
        nationality=row[7], maskapai_id=row[8], department=row[9],
        is_active=row[10], created_at=row[11], updated_at=row[12],
        user=SimpleNamespace(id=row[1], email=row[13], username=row[14],
                             first_name=row[15], last_name=row[16]),
    )


def _next_claim_id():
    with connection.cursor() as cursor:
        cursor.execute("SELECT claim_id FROM auth_system_claimmissingmiles ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
    if row:
        try:
            return f'CLM{int(row[0].replace("CLM", "")) + 1:06d}'
        except (ValueError, AttributeError):
            pass
    return 'CLM000001'


def _next_transfer_id():
    with connection.cursor() as cursor:
        cursor.execute("SELECT transfer_id FROM auth_system_transfermiles ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
    if row:
        try:
            return f'TRF{int(row[0].replace("TRF", "")) + 1:06d}'
        except (ValueError, AttributeError):
            pass
    return 'TRF000001'


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

    base_sql = """
        SELECT m.id, m.member_id, m.phone_number, m.total_miles, m.award_miles,
               m.is_active, m.created_at,
               u.email, u.first_name, u.last_name,
               t.tier_name
        FROM auth_system_member m
        JOIN auth_user u ON u.id = m.user_id
        LEFT JOIN auth_system_tier t ON t.id = m.tier_id
    """
    params = []
    if search_query:
        base_sql += """
            WHERE LOWER(m.member_id) LIKE LOWER(%s)
               OR LOWER(u.first_name) LIKE LOWER(%s)
               OR LOWER(u.last_name) LIKE LOWER(%s)
               OR LOWER(u.email) LIKE LOWER(%s)
        """
        like = f'%{search_query}%'
        params = [like, like, like, like]
    base_sql += " ORDER BY m.created_at DESC"

    with connection.cursor() as cursor:
        cursor.execute(base_sql, params)
        cols = [c[0] for c in cursor.description]
        rows = cursor.fetchall()

    members_data = []
    for r in rows:
        d = dict(zip(cols, r))
        members_data.append(SimpleNamespace(
            id=d['id'], member_id=d['member_id'], phone_number=d['phone_number'],
            total_miles=d['total_miles'], award_miles=d['award_miles'],
            is_active=d['is_active'], created_at=d['created_at'],
            user=SimpleNamespace(email=d['email'], first_name=d['first_name'],
                                 last_name=d['last_name']),
            tier=SimpleNamespace(tier_name=d['tier_name']) if d['tier_name'] else None,
        ))

    paginator = Paginator(members_data, 10)
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
            try:
                _, member = form.save()
                messages.success(request, f'Member {member.member_id} berhasil ditambahkan.')
                return redirect('auth_system:manage_members_list')
            except forms.ValidationError as e:
                form.add_error('email', e)
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

    member = _get_member_by_id(member_id)
    if member is None:
        raise Http404('Member tidak ditemukan')

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

    member = _get_member_by_id(member_id)
    if member is None:
        raise Http404('Member tidak ditemukan')

    deleted_member_id = member.member_id
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM auth_user WHERE id = %s", [member.user_id])
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
            try:
                user = form.save()
                login(request, user)
                messages.success(request, 'Akun Member berhasil dibuat! Selamat datang!')
                return redirect('auth_system:dashboard')
            except forms.ValidationError as e:
                form.add_error('email', e)
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
            try:
                user = form.save()
                login(request, user)
                messages.success(request, 'Akun Staff berhasil dibuat! Selamat datang!')
                return redirect('auth_system:dashboard')
            except forms.ValidationError as e:
                form.add_error('email', e)
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

    with connection.cursor() as cursor:
        cursor.execute(
            _CLAIM_BASE_SELECT + " WHERE c.member_id = %s ORDER BY c.created_at DESC",
            [member.id]
        )
        cols = [x[0] for x in cursor.description]
        claims = [_build_claim_ns(dict(zip(cols, r))) for r in cursor.fetchall()]
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
            cd = form.cleaned_data
            flight_number = cd['flight_number']
            ticket_number = cd.get('ticket_number', '')
            flight_date = cd['flight_date']

            duplicate_claim = check_duplicate_claim(
                member=member,
                flight_number=flight_number,
                ticket_number=ticket_number,
                flight_date=flight_date,
            )
            if duplicate_claim:
                messages.error(
                    request,
                    f'ERROR: Klaim untuk penerbangan "{flight_number}" pada tanggal "{flight_date}" sudah pernah diajukan sebelumnya.'
                )
                return render(request, 'auth_system/member_claim_form.html', {'form': form, 'title': 'Buat Claim Missing Miles'})

            claim_id = _next_claim_id()
            maskapai = cd.get('maskapai')
            bandara_asal = cd.get('bandara_asal')
            bandara_tujuan = cd.get('bandara_tujuan')
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO auth_system_claimmissingmiles
                                (member_id, claim_id, maskapai_id, bandara_asal_id, bandara_tujuan_id,
                                 kelas_kabin, pnr, flight_number, ticket_number, flight_date,
                                 miles_amount, status, reason, description, created_at, updated_at)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,'pending',%s,%s,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                        """, [
                            member.id, claim_id,
                            maskapai or None,
                            bandara_asal or None,
                            bandara_tujuan or None,
                            cd.get('kelas_kabin') or None,
                            cd.get('pnr') or None,
                            flight_number, ticket_number or None, flight_date,
                            cd['reason'], cd.get('description') or None,
                        ])
                messages.success(request, f'Claim berhasil dibuat dengan ID {claim_id}.')
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

    claim = _get_claim_by_id(claim_id, member_id=member.id)
    if claim is None:
        raise Http404('Claim tidak ditemukan')
    return render(request, 'auth_system/member_claim_detail.html', {'claim': claim})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def member_claim_update_view(request, claim_id):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    claim = _get_claim_by_id(claim_id, member_id=member.id)
    if claim is None:
        raise Http404('Claim tidak ditemukan')
    if claim.status != 'pending':
        messages.error(request, 'Hanya klaim dengan status Pending yang dapat diubah.')
        return redirect('auth_system:member_claim_list')

    if request.method == 'POST':
        form = ClaimMissingMilesForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            flight_number = cd['flight_number']
            ticket_number = cd.get('ticket_number', '')
            flight_date = cd['flight_date']

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
                    f'ERROR: Klaim untuk penerbangan "{flight_number}" pada tanggal "{flight_date}" sudah pernah diajukan sebelumnya.'
                )
                return render(request, 'auth_system/member_claim_form.html', {'form': form, 'title': f'Ubah Claim {claim.claim_id}'})

            maskapai = cd.get('maskapai')
            bandara_asal = cd.get('bandara_asal')
            bandara_tujuan = cd.get('bandara_tujuan')
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE auth_system_claimmissingmiles
                            SET maskapai_id=%s, bandara_asal_id=%s, bandara_tujuan_id=%s,
                                kelas_kabin=%s, pnr=%s, flight_number=%s, ticket_number=%s,
                                flight_date=%s, reason=%s, description=%s, updated_at=CURRENT_TIMESTAMP
                            WHERE id=%s
                        """, [
                            maskapai or None,
                            bandara_asal or None,
                            bandara_tujuan or None,
                            cd.get('kelas_kabin') or None,
                            cd.get('pnr') or None,
                            flight_number, ticket_number or None, flight_date,
                            cd['reason'], cd.get('description') or None,
                            claim.id,
                        ])
                messages.success(request, 'Claim berhasil diperbarui.')
                return redirect('auth_system:member_claim_list')
            except DatabaseError as exc:
                messages.error(request, _extract_db_error_message(exc))
    else:
        initial = {
            'maskapai': claim.maskapai_id,
            'bandara_asal': claim.bandara_asal_id,
            'bandara_tujuan': claim.bandara_tujuan_id,
            'kelas_kabin': claim.kelas_kabin,
            'pnr': claim.pnr,
            'flight_number': claim.flight_number,
            'ticket_number': claim.ticket_number,
            'flight_date': claim.flight_date,
            'reason': claim.reason,
            'description': claim.description,
        }
        form = ClaimMissingMilesForm(initial=initial)

    return render(request, 'auth_system/member_claim_form.html', {'form': form, 'title': f'Ubah Claim {claim.claim_id}'})


@require_http_methods(["POST"])
@login_required(login_url='auth_system:login')
def member_claim_delete_view(request, claim_id):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    claim = _get_claim_by_id(claim_id, member_id=member.id)
    if claim is None:
        raise Http404('Claim tidak ditemukan')
    if claim.status != 'pending':
        messages.error(request, 'Hanya klaim dengan status Pending yang dapat dihapus.')
        return redirect('auth_system:member_claim_list')
    claim_id_value = claim.claim_id
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM auth_system_claimmissingmiles WHERE id = %s", [claim.id])
    messages.success(request, f'Claim {claim_id_value} berhasil dihapus.')
    return redirect('auth_system:member_claim_list')


@login_required(login_url='auth_system:login')
def staff_claim_list_view(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    sql = """
        SELECT c.id, c.member_id, c.claim_id, c.flight_number, c.flight_date,
               c.ticket_number, c.miles_amount, c.status, c.reason, c.description,
               c.pnr, c.kelas_kabin, c.created_at, c.updated_at, c.approved_by_id,
               c.maskapai_id, mk.code AS maskapai_code, mk.name AS maskapai_name,
               ba.iata_code AS asal_iata, ba.nama AS asal_nama,
               bt.iata_code AS tujuan_iata, bt.nama AS tujuan_nama,
               m.member_id AS m_member_id, m.total_miles AS m_total_miles,
               u.username AS u_username, u.email AS u_email,
               t.tier_name AS t_tier_name
        FROM auth_system_claimmissingmiles c
        JOIN auth_system_member m ON m.id = c.member_id
        JOIN auth_user u ON u.id = m.user_id
        LEFT JOIN auth_system_tier t ON t.id = m.tier_id
        LEFT JOIN auth_system_maskapai mk ON mk.id = c.maskapai_id
        LEFT JOIN auth_system_bandara ba ON ba.iata_code = c.bandara_asal_id
        LEFT JOIN auth_system_bandara bt ON bt.iata_code = c.bandara_tujuan_id
        ORDER BY c.created_at DESC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        cols = [x[0] for x in cursor.description]
        claims = [_build_claim_ns(dict(zip(cols, r))) for r in cursor.fetchall()]
    return render(request, 'auth_system/staff_claim_list.html', {'staff': staff, 'claims': claims})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def staff_claim_update_view(request, claim_id):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    claim = _get_claim_by_id(claim_id)
    if claim is None:
        raise Http404('Claim tidak ditemukan')
    old_status = claim.status

    if request.method == 'POST':
        form = StaffClaimUpdateForm(request.POST, claim=claim)
        if form.is_valid():
            cd = form.cleaned_data
            new_status = cd['status']
            miles_amount = cd.get('miles_amount') or claim.miles_amount
            description = cd.get('description') or ''
            old_tier_name = claim.member.tier.get_tier_name_display() if claim.member.tier else 'Tidak ada'

            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE auth_system_claimmissingmiles
                            SET status=%s, miles_amount=%s, approved_by_id=%s, description=%s, updated_at=CURRENT_TIMESTAMP
                            WHERE id=%s
                        """, [new_status, miles_amount, staff.id, description, claim.id])

                        if old_status != 'approved' and new_status == 'approved' and miles_amount:
                            cursor.execute("""
                                UPDATE auth_system_member
                                SET total_miles = total_miles + %s, updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                            """, [miles_amount, claim.member.id])

                            if connection.vendor == 'postgresql':
                                cursor.execute('SELECT sp_auto_update_member_tier(%s);', [claim.member.id])

                    if old_status != 'approved' and new_status == 'approved' and miles_amount:
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                SELECT t.tier_name FROM auth_system_member m
                                LEFT JOIN auth_system_tier t ON t.id = m.tier_id
                                WHERE m.id = %s
                            """, [claim.member.id])
                            tier_row = cursor.fetchone()
                        new_tier_raw = tier_row[0] if tier_row else None
                        new_tier_name = dict([('bronze','Bronze'),('silver','Silver'),
                                              ('gold','Gold'),('platinum','Platinum')]).get(
                                                  new_tier_raw, 'Tidak ada') if new_tier_raw else 'Tidak ada'
                        if old_tier_name != new_tier_name:
                            messages.success(
                                request,
                                f'Claim {claim.claim_id} disetujui. Tier member diperbarui dari "{old_tier_name}" ke "{new_tier_name}".'
                            )
                        else:
                            messages.success(
                                request,
                                f'Claim {claim.claim_id} disetujui. {miles_amount:,} miles ditambahkan ke member.'
                            )
                    else:
                        messages.success(request, f'Claim {claim.claim_id} berhasil diperbarui.')

                return redirect('auth_system:staff_claim_list')
            except DatabaseError as exc:
                messages.error(request, _extract_db_error_message(exc))
    else:
        form = StaffClaimUpdateForm(claim=claim)

    return render(request, 'auth_system/staff_claim_form.html', {'form': form, 'claim': claim})


@login_required(login_url='auth_system:login')
@require_http_methods(["GET"])
def staff_transaction_report_view(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    with connection.cursor() as cursor:
        # Summary: total miles awarded via approved claims
        cursor.execute("""
            SELECT COALESCE(SUM(miles_amount), 0)
            FROM auth_system_claimmissingmiles
            WHERE status IN ('approved', 'processed') AND miles_amount IS NOT NULL
        """)
        total_claimed_miles = cursor.fetchone()[0]

        # Total award miles redeemed
        cursor.execute("SELECT COALESCE(SUM(miles_used), 0) FROM auth_system_redeem")
        total_redeemed_miles = cursor.fetchone()[0]

        # Total award miles purchased via packages
        cursor.execute("""
            SELECT COALESCE(SUM(a.jumlah_award_miles), 0)
            FROM auth_system_memberawardmilespackage mp
            JOIN auth_system_awardmilespackage a ON a.id = mp.award_miles_package_id
        """)
        total_purchased_miles = cursor.fetchone()[0]

        # Transactions: Transfer
        cursor.execute("""
            SELECT 'Transfer' AS type, t.created_at, u.first_name || ' ' || u.last_name AS member_name,
                   u.email, t.miles_amount, t.transfer_id AS ref_id
            FROM auth_system_transfermiles t
            JOIN auth_system_member m ON m.id = t.from_member_id
            JOIN auth_user u ON u.id = m.user_id
            WHERE t.status = 'completed'
            ORDER BY t.created_at DESC LIMIT 50
        """)
        transfers_raw = cursor.fetchall()

        # Transactions: Redeem
        cursor.execute("""
            SELECT 'Redeem' AS type, r.timestamp, u.first_name || ' ' || u.last_name AS member_name,
                   u.email, r.miles_used, h.kode_hadiah AS ref_id
            FROM auth_system_redeem r
            JOIN auth_system_member m ON m.id = r.member_id
            JOIN auth_user u ON u.id = m.user_id
            JOIN auth_system_hadiah h ON h.id = r.hadiah_id
            ORDER BY r.timestamp DESC LIMIT 50
        """)
        redeems_raw = cursor.fetchall()

        # Transactions: Package purchase
        cursor.execute("""
            SELECT 'Package' AS type, mp.timestamp, u.first_name || ' ' || u.last_name AS member_name,
                   u.email, a.jumlah_award_miles, a.id AS ref_id
            FROM auth_system_memberawardmilespackage mp
            JOIN auth_system_member m ON m.id = mp.member_id
            JOIN auth_user u ON u.id = m.user_id
            JOIN auth_system_awardmilespackage a ON a.id = mp.award_miles_package_id
            ORDER BY mp.timestamp DESC LIMIT 50
        """)
        packages_raw = cursor.fetchall()

        # Top members by total_miles
        cursor.execute("""
            SELECT u.first_name || ' ' || u.last_name AS name, u.email, m.total_miles, m.member_id
            FROM auth_system_member m
            JOIN auth_user u ON u.id = m.user_id
            ORDER BY m.total_miles DESC LIMIT 10
        """)
        top_members_raw = cursor.fetchall()

    icon_map = {'Transfer': 'fa-right-left', 'Redeem': 'fa-gift', 'Package': 'fa-cart-shopping'}
    transactions = []
    for txn_type, ts, name, email, miles, ref_id in sorted(
        list(transfers_raw) + list(redeems_raw) + list(packages_raw),
        key=lambda r: r[1], reverse=True
    )[:50]:
        is_positive = txn_type == 'Package'
        transactions.append({
            'type': txn_type,
            'icon': icon_map.get(txn_type, 'fa-circle'),
            'member': name,
            'email': email,
            'miles': f'{"-" if not is_positive else "+"}{miles:,}',
            'is_positive': is_positive,
            'timestamp': ts,
            'ref_id': ref_id,
        })

    top_members = [
        {'rank': i + 1, 'name': name, 'email': email, 'total_miles': f'{miles:,}', 'member_id': mid}
        for i, (name, email, miles, mid) in enumerate(top_members_raw)
    ]

    summary = {
        'total_claimed_miles': f'{total_claimed_miles:,}',
        'total_redeemed_miles': f'{total_redeemed_miles:,}',
        'total_purchased_miles': f'{total_purchased_miles:,}',
    }

    for txn in transactions:
        txn['can_delete'] = txn['type'] in ('Transfer', 'Redeem', 'Package')

    context = {
        'staff': staff,
        'summary': summary,
        'transactions': transactions,
        'top_members': top_members,
    }
    return render(request, 'staff/report/staff_transaction_report.html', context)


@require_http_methods(["POST"])
@login_required(login_url='auth_system:login')
def staff_transaction_delete_view(request):
    staff = _get_staff(request.user)
    if not staff:
        return redirect('auth_system:dashboard')

    txn_type = request.POST.get('type', '')
    ref_id = request.POST.get('ref_id', '')

    try:
        with connection.cursor() as cursor:
            if txn_type == 'Transfer':
                cursor.execute(
                    "DELETE FROM auth_system_transfermiles WHERE transfer_id = %s",
                    [ref_id]
                )
            elif txn_type == 'Redeem':
                cursor.execute(
                    "DELETE FROM auth_system_redeem WHERE id = %s",
                    [ref_id]
                )
            elif txn_type == 'Package':
                cursor.execute(
                    "DELETE FROM auth_system_memberawardmilespackage WHERE id = %s",
                    [ref_id]
                )
        messages.success(request, 'Riwayat transaksi berhasil dihapus.')
    except DatabaseError as exc:
        messages.error(request, _extract_db_error_message(exc))

    return redirect('auth_system:staff_transaction_report')


@login_required(login_url='auth_system:login')
def member_transfer_list_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT t.id, t.transfer_id, t.miles_amount, t.status, t.description, t.created_at,
                   uf.email AS from_email, mf.member_id AS from_member_id,
                   ut.email AS to_email, mt.member_id AS to_member_id,
                   (t.from_member_id = %s) AS is_sender
            FROM auth_system_transfermiles t
            JOIN auth_system_member mf ON mf.id = t.from_member_id
            JOIN auth_user uf ON uf.id = mf.user_id
            JOIN auth_system_member mt ON mt.id = t.to_member_id
            JOIN auth_user ut ON ut.id = mt.user_id
            WHERE t.from_member_id = %s OR t.to_member_id = %s
            ORDER BY t.created_at DESC
        """, [member.id, member.id, member.id])
        cols = [c[0] for c in cursor.description]
        transfers = [dict(zip(cols, row)) for row in cursor.fetchall()]

    return render(request, 'auth_system/member_transfer_list.html', {'member': member, 'transfers': transfers})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def member_redeem_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    if request.method == 'POST':
        hadiah_id = request.POST.get('hadiah_id')
        if not hadiah_id:
            messages.error(request, 'Hadiah tidak valid.')
            return redirect('auth_system:member_redeem')

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Lock member row and check award_miles
                    cursor.execute(
                        "SELECT award_miles FROM auth_system_member WHERE id = %s FOR UPDATE",
                        [member.id]
                    )
                    member_row = cursor.fetchone()

                    # Fetch hadiah
                    cursor.execute("""
                        SELECT id, miles_diperlukan, jumlah_tersedia, jumlah_terjual, nama_hadiah,
                               tanggal_valid_mulai, tanggal_valid_akhir, status
                        FROM auth_system_hadiah WHERE id = %s FOR UPDATE
                    """, [hadiah_id])
                    hadiah_row = cursor.fetchone()

                    if not hadiah_row:
                        messages.error(request, 'Hadiah tidak ditemukan.')
                        return redirect('auth_system:member_redeem')

                    h_id, h_miles, h_tersedia, h_terjual, h_nama, h_mulai, h_akhir, h_status = hadiah_row

                    if h_status != 'active':
                        messages.error(request, 'Hadiah tidak aktif.')
                        return redirect('auth_system:member_redeem')

                    today = date.today()
                    if not (h_mulai <= today <= h_akhir):
                        messages.error(request, 'Periode hadiah tidak berlaku.')
                        return redirect('auth_system:member_redeem')

                    sisa = h_tersedia - h_terjual
                    if sisa <= 0:
                        messages.error(request, 'Stok hadiah habis.')
                        return redirect('auth_system:member_redeem')

                    award_miles = member_row[0]
                    if award_miles < h_miles:
                        messages.error(request, f'Award miles tidak mencukupi. Dibutuhkan {h_miles:,}, dimiliki {award_miles:,}.')
                        return redirect('auth_system:member_redeem')

                    # Insert redeem record
                    cursor.execute("""
                        INSERT INTO auth_system_redeem (member_id, hadiah_id, timestamp, miles_used)
                        VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
                    """, [member.id, h_id, h_miles])

                    # Deduct award_miles
                    cursor.execute("""
                        UPDATE auth_system_member SET award_miles = award_miles - %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, [h_miles, member.id])

                    # Increment jumlah_terjual
                    cursor.execute("""
                        UPDATE auth_system_hadiah SET jumlah_terjual = jumlah_terjual + 1, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, [h_id])

                messages.success(request, f'Berhasil menukar hadiah "{h_nama}" dengan {h_miles:,} award miles.')
                return redirect('auth_system:member_redeem')
        except DatabaseError as exc:
            messages.error(request, _extract_db_error_message(exc))
            return redirect('auth_system:member_redeem')

    # GET: load available rewards and redeem history
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT h.id, h.kode_hadiah, h.nama_hadiah, h.miles_diperlukan, h.deskripsi,
                   h.tanggal_valid_mulai, h.tanggal_valid_akhir, h.jumlah_tersedia, h.jumlah_terjual,
                   p.name AS penyedia_name
            FROM auth_system_hadiah h
            JOIN auth_system_penyedia p ON p.id = h.penyedia_id
            WHERE h.status = 'active'
              AND h.tanggal_valid_mulai <= %s
              AND h.tanggal_valid_akhir >= %s
              AND h.jumlah_tersedia > h.jumlah_terjual
            ORDER BY h.miles_diperlukan
        """, [date.today(), date.today()])
        cols = [c[0] for c in cursor.description]
        available_rewards = [dict(zip(cols, row)) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT r.timestamp, r.miles_used, h.nama_hadiah
            FROM auth_system_redeem r
            JOIN auth_system_hadiah h ON h.id = r.hadiah_id
            WHERE r.member_id = %s
            ORDER BY r.timestamp DESC
        """, [member.id])
        cols2 = [c[0] for c in cursor.description]
        redeem_history = [dict(zip(cols2, row)) for row in cursor.fetchall()]

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

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT h.id, h.kode_hadiah, h.nama_hadiah, h.miles_diperlukan, h.deskripsi,
                   h.tanggal_valid_mulai, h.tanggal_valid_akhir, h.status,
                   h.jumlah_tersedia, h.jumlah_terjual, p.name AS penyedia_name
            FROM auth_system_hadiah h
            JOIN auth_system_penyedia p ON p.id = h.penyedia_id
            ORDER BY h.status, h.miles_diperlukan
        """)
        cols = [c[0] for c in cursor.description]
        all_rewards = [dict(zip(cols, row)) for row in cursor.fetchall()]

    today = date.today()
    active_rewards = [
        r for r in all_rewards
        if r['status'] == 'active'
        and r['tanggal_valid_mulai'] <= today <= r['tanggal_valid_akhir']
    ]

    context = {
        'staff': staff,
        'rewards': all_rewards,
        'active_rewards': active_rewards,
    }
    return render(request, 'staff/reward/staff_rewards.html', context)


@login_required(login_url='auth_system:login')
def staff_partners_view(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, code, contact_person, email, phone_number, is_active, created_at
            FROM auth_system_mitra
            ORDER BY is_active DESC, name
        """)
        cols = [c[0] for c in cursor.description]
        partners = [dict(zip(cols, row)) for row in cursor.fetchall()]

    context = {
        'staff': staff,
        'partners': partners,
    }
    return render(request, 'staff/partner/staff_partners.html', context)


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def staff_mitra_create_view(request):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    if request.method == 'POST':
        form = MitraForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO auth_system_mitra
                                (name, code, contact_person, email, phone_number,
                                 tanggal_kerja_sama, is_active, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, [
                            cd['name'], cd['code'],
                            cd.get('contact_person') or None,
                            cd['email'],
                            cd.get('phone_number') or None,
                            cd.get('tanggal_kerja_sama') or None,
                            cd.get('is_active', True),
                        ])
                        cursor.execute(
                            "SELECT 1 FROM auth_system_penyedia WHERE LOWER(code) = LOWER(%s) LIMIT 1",
                            [cd['code']]
                        )
                        if cursor.fetchone() is None:
                            cursor.execute("""
                                INSERT INTO auth_system_penyedia
                                    (name, code, contact_person, email, phone_number, is_active, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """, [
                                cd['name'], cd['code'],
                                cd.get('contact_person') or None,
                                cd['email'],
                                cd.get('phone_number') or None,
                                cd.get('is_active', True),
                            ])
                messages.success(request, f'Mitra "{cd["name"]}" berhasil ditambahkan dan didaftarkan sebagai Penyedia.')
                return redirect('auth_system:staff_partners')
            except DatabaseError as exc:
                messages.error(request, _extract_db_error_message(exc))
    else:
        form = MitraForm()

    return render(request, 'staff/partner/mitra_form.html', {'form': form, 'staff': staff, 'title': 'Tambah Mitra'})


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def staff_mitra_edit_view(request, mitra_id):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    mitra = _get_mitra_by_id(mitra_id)
    if mitra is None:
        raise Http404('Mitra tidak ditemukan')

    if request.method == 'POST':
        form = MitraForm(request.POST, mitra=mitra)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE auth_system_mitra
                        SET name=%s, code=%s, contact_person=%s, email=%s,
                            phone_number=%s, tanggal_kerja_sama=%s, is_active=%s, updated_at=CURRENT_TIMESTAMP
                        WHERE id=%s
                    """, [
                        cd['name'], cd['code'],
                        cd.get('contact_person') or None,
                        cd['email'],
                        cd.get('phone_number') or None,
                        cd.get('tanggal_kerja_sama') or None,
                        cd.get('is_active', True),
                        mitra_id,
                    ])
                messages.success(request, f'Mitra "{cd["name"]}" berhasil diperbarui.')
                return redirect('auth_system:staff_partners')
            except DatabaseError as exc:
                messages.error(request, _extract_db_error_message(exc))
    else:
        form = MitraForm(mitra=mitra)

    return render(request, 'staff/partner/mitra_form.html', {'form': form, 'staff': staff, 'mitra': mitra, 'title': 'Edit Mitra'})


@require_http_methods(["POST"])
@login_required(login_url='auth_system:login')
def staff_mitra_delete_view(request, mitra_id):
    staff = _get_staff(request.user)
    if not staff:
        messages.error(request, 'Halaman ini hanya untuk staff.')
        return redirect('auth_system:dashboard')

    mitra = _get_mitra_by_id(mitra_id)
    if mitra is None:
        raise Http404('Mitra tidak ditemukan')
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_system_mitra WHERE id = %s", [mitra_id])
        messages.success(request, f'Mitra "{mitra.name}" berhasil dihapus.')
    except DatabaseError as exc:
        messages.error(request, _extract_db_error_message(exc))
    return redirect('auth_system:staff_partners')


@require_http_methods(["GET", "POST"])
@login_required(login_url='auth_system:login')
def member_package_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    if request.method == 'POST':
        package_id = request.POST.get('package_id')
        if not package_id:
            messages.error(request, 'Paket tidak valid.')
            return redirect('auth_system:member_package')

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, jumlah_award_miles, harga_paket
                        FROM auth_system_awardmilespackage
                        WHERE id = %s
                    """, [package_id])
                    pkg_row = cursor.fetchone()
                    if not pkg_row:
                        messages.error(request, 'Paket tidak ditemukan.')
                        return redirect('auth_system:member_package')

                    pkg_id, pkg_miles, pkg_price = pkg_row

                    cursor.execute("""
                        INSERT INTO auth_system_memberawardmilespackage
                            (award_miles_package_id, member_id, timestamp)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                    """, [pkg_id, member.id])

                    cursor.execute("""
                        UPDATE auth_system_member
                        SET award_miles = award_miles + %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, [pkg_miles, member.id])

            messages.success(request, f'Berhasil membeli paket {pkg_id}. {pkg_miles:,} award miles ditambahkan ke akun Anda.')
            return redirect('auth_system:member_package')
        except DatabaseError as exc:
            messages.error(request, _extract_db_error_message(exc))

    # GET: load packages and purchase history
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, jumlah_award_miles, harga_paket
            FROM auth_system_awardmilespackage
            ORDER BY jumlah_award_miles
        """)
        cols = [c[0] for c in cursor.description]
        packages = [dict(zip(cols, row)) for row in cursor.fetchall()]

        cursor.execute("""
            SELECT mp.timestamp, a.id AS package_id, a.jumlah_award_miles, a.harga_paket
            FROM auth_system_memberawardmilespackage mp
            JOIN auth_system_awardmilespackage a ON a.id = mp.award_miles_package_id
            WHERE mp.member_id = %s
            ORDER BY mp.timestamp DESC
        """, [member.id])
        cols2 = [c[0] for c in cursor.description]
        purchase_history = [dict(zip(cols2, row)) for row in cursor.fetchall()]

    context = {
        'member': member,
        'packages': packages,
        'purchase_history': purchase_history,
    }
    return render(request, 'member/package/member_package.html', context)


@login_required(login_url='auth_system:login')
def member_tier_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT tier_name, minimal_tier_miles, minimal_frekuensi_terbang
            FROM auth_system_tier
            WHERE is_active = TRUE
            ORDER BY minimal_tier_miles
        """)
        rows = cursor.fetchall()

    tier_colors = {
        'bronze': '#cd7f32',
        'silver': '#8b98a8',
        'gold': '#d4a72c',
        'platinum': '#111827',
    }
    tiers = []
    for tier_name, min_miles, min_freq in rows:
        tiers.append({
            'code': tier_name,
            'name': tier_name.capitalize(),
            'miles_min': min_miles,
            'flight_min': min_freq,
            'color': tier_colors.get(tier_name, '#6c757d'),
        })

    current_tier = tiers[0] if tiers else None
    for t in tiers:
        if member.total_miles >= t['miles_min']:
            current_tier = t

    current_index = tiers.index(current_tier) if current_tier in tiers else 0
    next_tier = tiers[current_index + 1] if current_index + 1 < len(tiers) else None

    if next_tier and current_tier:
        progress_start = current_tier['miles_min']
        progress_target = next_tier['miles_min']
        progress_range = progress_target - progress_start
        progress_value = max(0, member.total_miles - progress_start)
        progress_percent = min(100, int((progress_value / progress_range) * 100)) if progress_range else 100
    else:
        progress_target = current_tier['miles_min'] if current_tier else 0
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
            miles_amount = form.cleaned_data['miles_amount']
            to_member = form.to_member
            description = form.cleaned_data.get('description', '')
            transfer_id = _next_transfer_id()

            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        # Lock rows and check award_miles balance
                        cursor.execute(
                            "SELECT award_miles FROM auth_system_member WHERE id = %s FOR UPDATE",
                            [member.id]
                        )
                        row = cursor.fetchone()
                        if not row or row[0] < miles_amount:
                            form.add_error('miles_amount', 'Award miles tidak mencukupi untuk transfer ini.')
                        else:
                            cursor.execute(
                                "SELECT id FROM auth_system_member WHERE id = %s FOR UPDATE",
                                [to_member.id]
                            )
                            cursor.execute("""
                                INSERT INTO auth_system_transfermiles
                                    (from_member_id, to_member_id, transfer_id, miles_amount, status, description, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, 'completed', %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """, [member.id, to_member.id, transfer_id, miles_amount, description])

                            cursor.execute("""
                                UPDATE auth_system_member
                                SET award_miles = award_miles - %s, updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                            """, [miles_amount, member.id])

                            cursor.execute("""
                                UPDATE auth_system_member
                                SET award_miles = award_miles + %s, updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                            """, [miles_amount, to_member.id])

                            messages.success(request, f'Transfer berhasil dengan ID {transfer_id}.')
                            return redirect('auth_system:member_transfer_list')
            except DatabaseError as exc:
                messages.error(request, _extract_db_error_message(exc))
    else:
        form = TransferMilesForm(from_member=member)

    return render(request, 'auth_system/member_transfer_form.html', {'form': form, 'member': member})


@login_required(login_url='auth_system:login')
def member_identities_list_view(request):
    member = _get_member(request.user)
    if not member:
        messages.error(request, 'Halaman ini hanya untuk member.')
        return redirect('auth_system:dashboard')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, document_number, document_type, country, issue_date,
                   expiry_date, is_expired, created_at, updated_at
            FROM auth_system_identity
            WHERE member_id = %s
            ORDER BY created_at DESC
        """, [member.id])
        cols = [c[0] for c in cursor.description]
        identities = [SimpleNamespace(**dict(zip(cols, r))) for r in cursor.fetchall()]
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

    penyedia_id = request.GET.get('penyedia', '')
    status = request.GET.get('status', '')

    sql = """
        SELECT h.id, h.kode_hadiah, h.nama_hadiah, h.deskripsi,
               h.miles_diperlukan, h.tanggal_valid_mulai, h.tanggal_valid_akhir,
               h.is_active, h.created_at, h.updated_at,
               p.id AS p_id, p.name AS p_name, p.code AS p_code,
               mt.id AS mt_id, mt.name AS mt_name, mt.code AS mt_code
        FROM auth_system_hadiah h
        LEFT JOIN auth_system_penyedia p ON p.id = h.penyedia_id
        LEFT JOIN auth_system_mitra mt ON mt.id = h.mitra_id
    """
    where, params = [], []
    if penyedia_id:
        where.append("h.penyedia_id = %s")
        params.append(penyedia_id)
    if status:
        where.append("h.is_active = %s")
        params.append(status == 'active')
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY h.created_at DESC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        cols = [c[0] for c in cursor.description]
        rows = cursor.fetchall()

    hadiah_list = []
    for r in rows:
        d = dict(zip(cols, r))
        h = SimpleNamespace(
            id=d['id'], kode_hadiah=d['kode_hadiah'], nama_hadiah=d['nama_hadiah'],
            deskripsi=d['deskripsi'], miles_diperlukan=d['miles_diperlukan'],
            tanggal_valid_mulai=d['tanggal_valid_mulai'],
            tanggal_valid_akhir=d['tanggal_valid_akhir'],
            is_active=d['is_active'], created_at=d['created_at'],
            updated_at=d['updated_at'],
        )
        h.penyedia = SimpleNamespace(id=d['p_id'], name=d['p_name'], code=d['p_code']) if d['p_id'] else None
        h.mitra = SimpleNamespace(id=d['mt_id'], name=d['mt_name'], code=d['mt_code']) if d['mt_id'] else None
        hadiah_list.append(h)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, name FROM auth_system_penyedia
            WHERE is_active = TRUE ORDER BY name
        """)
        penyedia_list = cursor.fetchall()

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

    hadiah = _get_hadiah_by_id(hadiah_id)
    if hadiah is None:
        raise Http404('Hadiah tidak ditemukan')

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

    hadiah = _get_hadiah_by_id(hadiah_id)
    if not hadiah:
        raise Http404

    if request.method == 'POST':
        form = HadiahForm(request.POST, hadiah_id=hadiah_id)
        if form.is_valid():
            updated_hadiah = form.save()
            messages.success(request, f'Hadiah "{updated_hadiah.nama_hadiah}" berhasil diperbarui.')
            return redirect('auth_system:staff_hadiah_detail', hadiah_id=hadiah.id)
    else:
        form = HadiahForm(initial={
            'kode_hadiah': hadiah.kode_hadiah,
            'nama_hadiah': hadiah.nama_hadiah,
            'penyedia': str(hadiah.penyedia_id) if hadiah.penyedia_id else '',
            'miles_diperlukan': hadiah.miles_diperlukan,
            'deskripsi': hadiah.deskripsi,
            'tanggal_valid_mulai': hadiah.tanggal_valid_mulai,
            'tanggal_valid_akhir': hadiah.tanggal_valid_akhir,
        }, hadiah_id=hadiah_id)

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

    hadiah = _get_hadiah_by_id(hadiah_id)
    if not hadiah:
        raise Http404
    nama_hadiah = hadiah.nama_hadiah

    from datetime import date as _date
    if not (hadiah.tanggal_valid_akhir and hadiah.tanggal_valid_akhir < _date.today()):
        messages.error(request, 'Hadiah hanya dapat dihapus jika periode validitasnya sudah selesai.')
        return redirect('auth_system:staff_hadiah_detail', hadiah_id=hadiah.id)

    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_system_hadiah WHERE id = %s", [hadiah_id])
        messages.success(request, f'Hadiah "{nama_hadiah}" berhasil dihapus.')
        return redirect('auth_system:staff_hadiah_list')

    context = {
        'hadiah': hadiah,
        'staff': staff,
    }
    return render(request, 'staff/hadiah/hadiah_confirm_delete.html', context)
