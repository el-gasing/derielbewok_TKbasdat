import re
from datetime import date

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.utils.html import strip_tags
from django.db import connection, DatabaseError
from .models import Bandara, ClaimMissingMiles, Identity, Maskapai, Member, Staff, Mitra


def _sanitize_text(value, max_length=None):
    """Membersihkan input teks dari tag HTML dan karakter kontrol."""
    if value is None:
        return ""

    cleaned = strip_tags(str(value))
    cleaned = re.sub(r"[\x00-\x1F\x7F]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if max_length is not None:
        cleaned = cleaned[:max_length]

    return cleaned


def _sanitize_phone(value):
    cleaned = _sanitize_text(value, max_length=20)
    return re.sub(r"[^0-9+()\-\s]", "", cleaned)


COUNTRY_CODE_CHOICES = [
    ('+62', '+62'),
    ('+60', '+60'),
    ('+65', '+65'),
    ('+1', '+1'),
    ('+44', '+44'),
]


NATIONALITY_CHOICES = [
    ('Afghanistan', 'Afghanistan'),
    ('Armenia', 'Armenia'),
    ('Azerbaijan', 'Azerbaijan'),
    ('Bahrain', 'Bahrain'),
    ('Bangladesh', 'Bangladesh'),
    ('Bhutan', 'Bhutan'),
    ('Brunei Darussalam', 'Brunei Darussalam'),
    ('Cambodia', 'Cambodia'),
    ('China', 'China'),
    ('Cyprus', 'Cyprus'),
    ('Georgia', 'Georgia'),
    ('India', 'India'),
    ('Indonesia', 'Indonesia'),
    ('Iran', 'Iran'),
    ('Iraq', 'Iraq'),
    ('Israel', 'Israel'),
    ('Japan', 'Japan'),
    ('Jordan', 'Jordan'),
    ('Kazakhstan', 'Kazakhstan'),
    ('Kuwait', 'Kuwait'),
    ('Kyrgyzstan', 'Kyrgyzstan'),
    ('Laos', 'Laos'),
    ('Lebanon', 'Lebanon'),
    ('Malaysia', 'Malaysia'),
    ('Maldives', 'Maldives'),
    ('Mongolia', 'Mongolia'),
    ('Myanmar', 'Myanmar'),
    ('Nepal', 'Nepal'),
    ('North Korea', 'North Korea'),
    ('Oman', 'Oman'),
    ('Pakistan', 'Pakistan'),
    ('Palestine', 'Palestine'),
    ('Philippines', 'Philippines'),
    ('Qatar', 'Qatar'),
    ('Saudi Arabia', 'Saudi Arabia'),
    ('Singapore', 'Singapore'),
    ('South Korea', 'South Korea'),
    ('Sri Lanka', 'Sri Lanka'),
    ('Syria', 'Syria'),
    ('Taiwan', 'Taiwan'),
    ('Tajikistan', 'Tajikistan'),
    ('Thailand', 'Thailand'),
    ('Timor-Leste', 'Timor-Leste'),
    ('Turkey', 'Turkey'),
    ('Turkmenistan', 'Turkmenistan'),
    ('United Arab Emirates', 'United Arab Emirates'),
    ('Uzbekistan', 'Uzbekistan'),
    ('Vietnam', 'Vietnam'),
    ('Yemen', 'Yemen'),
]

DEFAULT_MASKAPAI = [
    {'code': 'GA', 'name': 'Garuda Indonesia'},
    {'code': 'QG', 'name': 'Citilink'},
    {'code': 'QZ', 'name': 'AirAsia Indonesia'},
    {'code': 'JT', 'name': 'Lion Air'},
    {'code': 'ID', 'name': 'Batik Air'},
]

DEFAULT_PENYEDIA = [
    {'code': 'GAR', 'name': 'Garuda Indonesia'},
    {'code': 'TRV', 'name': 'Traveloka Partner'},
    {'code': 'PLZ', 'name': 'Plaza Premium'},
]

DEFAULT_MITRA = [
    {'code': 'TRV', 'name': 'Traveloka Partner'},
    {'code': 'PLZ', 'name': 'Plaza Premium'},
]


def _email_exists(email, exclude_user_id=None):
    sql = "SELECT 1 FROM auth_user WHERE LOWER(email) = LOWER(%s)"
    params = [email]
    if exclude_user_id is not None:
        sql += " AND id <> %s"
        params.append(exclude_user_id)
    sql += " LIMIT 1"
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone() is not None


def _extract_trigger_msg(e):
    first_line = str(e).split('\n')[0].strip()
    while first_line.upper().startswith('ERROR:'):
        first_line = first_line[6:].strip()
    return first_line or str(e).split('\n')[0]


def _username_exists(username):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM auth_user WHERE username = %s LIMIT 1", [username]
        )
        return cursor.fetchone() is not None


def _build_unique_username(email):
    base = (email or '').split('@')[0]
    base = re.sub(r'[^a-zA-Z0-9_.-]', '', base).lower() or 'user'
    username = base[:150]
    suffix = 1

    while _username_exists(username):
        extra = str(suffix)
        username = f"{base[:max(1, 150 - len(extra))]}{extra}"
        suffix += 1

    return username


def _seed_default(table_name, items):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
        if cursor.fetchone():
            return
        for item in items:
            cursor.execute(
                f"""INSERT INTO {table_name}
                    (name, code, email, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                [item['name'], item['code'],
                 f"{item['code'].lower()}@aeromiles.local"]
            )


def _ensure_default_maskapai():
    _seed_default('auth_system_maskapai', DEFAULT_MASKAPAI)


def _ensure_default_penyedia():
    _seed_default('auth_system_penyedia', DEFAULT_PENYEDIA)


def _ensure_default_mitra():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM auth_system_mitra LIMIT 1")
        if cursor.fetchone():
            return
        for item in DEFAULT_MITRA:
            cursor.execute(
                """INSERT INTO auth_system_mitra
                    (name, code, email, is_active, tanggal_kerja_sama, created_at, updated_at)
                    VALUES (%s, %s, %s, TRUE, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                [item['name'], item['code'],
                 f"{item['code'].lower()}@aeromiles.local"]
            )


class LoginForm(AuthenticationForm):
    """Form untuk login dengan username dan password"""
    username = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username atau Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'password')

    def clean_username(self):
        """Convert email to username jika input menggunakan email"""
        username_input = self.cleaned_data.get('username', '').strip()
        
        if not username_input:
            raise forms.ValidationError('Username atau email harus diisi.')
        
        if '@' in username_input:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT username FROM auth_user
                       WHERE LOWER(email) = LOWER(%s)
                       ORDER BY last_login DESC LIMIT 1""",
                    [username_input]
                )
                row = cursor.fetchone()
            if row:
                return row[0]
            raise forms.ValidationError('Email tidak terdaftar.')

        return username_input


class MemberRegistrationForm(UserCreationForm):
    """Form untuk registrasi Member"""
    username = forms.CharField(required=False, widget=forms.HiddenInput())
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    salutation = forms.ChoiceField(
        choices=[('', 'Pilih')] + Member.SALUTATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    first_name = forms.CharField(
        max_length=50,
        label='Nama Depan-Tengah',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nama depan-tengah'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nama Belakang'
        })
    )
    country_code = forms.ChoiceField(
        choices=COUNTRY_CODE_CHOICES,
        initial='+62',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nomor Telepon'
        })
    )
    birth_date = forms.DateField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    nationality = forms.ChoiceField(
        choices=[('', 'Pilih negara')] + NATIONALITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Konfirmasi Password'})

    def save(self, commit=True):
        from django.contrib.auth.hashers import make_password
        if not commit:
            user = super().save(commit=False)
            user.username = self.cleaned_data['username']
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            return user

        hashed_pwd = make_password(self.cleaned_data['password1'])
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO auth_user
                        (username, email, first_name, last_name, password,
                         is_superuser, is_staff, is_active, date_joined)
                    VALUES (%s, %s, %s, %s, %s, FALSE, FALSE, TRUE, CURRENT_TIMESTAMP)
                    RETURNING id
                """, [
                    self.cleaned_data['username'], self.cleaned_data['email'],
                    self.cleaned_data['first_name'], self.cleaned_data['last_name'],
                    hashed_pwd,
                ])
                user_id = cursor.fetchone()[0]

                cursor.execute("SELECT member_id FROM auth_system_member ORDER BY id DESC LIMIT 1")
                last = cursor.fetchone()
                if last:
                    try:
                        next_num = int(last[0].replace('AMS', '')) + 1
                    except (ValueError, AttributeError):
                        next_num = 1
                else:
                    next_num = 1
                member_id_val = f"AMS{next_num:06d}"

                cursor.execute("""
                    INSERT INTO auth_system_member
                        (user_id, member_id, salutation, country_code, phone_number,
                         birth_date, nationality, total_miles, award_miles, is_active,
                         created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, [
                    user_id, member_id_val, self.cleaned_data['salutation'],
                    self.cleaned_data['country_code'], self.cleaned_data['phone_number'],
                    self.cleaned_data['birth_date'], self.cleaned_data['nationality'],
                ])
        except DatabaseError as e:
            raise forms.ValidationError(_extract_trigger_msg(e))
        return User.objects.get(pk=user_id)

    def clean_username(self):
        return _build_unique_username(self.cleaned_data.get('email', ''))

    def clean_first_name(self):
        return _sanitize_text(self.cleaned_data.get('first_name'), max_length=50)

    def clean_last_name(self):
        return _sanitize_text(self.cleaned_data.get('last_name'), max_length=50)

    def clean_phone_number(self):
        return _sanitize_phone(self.cleaned_data.get('phone_number'))

    def clean_birth_date(self):
        value = self.cleaned_data.get('birth_date')
        if value and value > date.today():
            raise forms.ValidationError('Tanggal lahir tidak valid.')
        return value

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError('Email harus diisi.')
        return email


class StaffMemberCreateForm(UserCreationForm):
    """Form untuk staff menambahkan member baru."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    first_name = forms.CharField(
        max_length=50,
        label='Nama Depan',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nama depan'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        label='Nama Belakang',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nama Belakang'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nomor HP'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Konfirmasi Password'})

    def save(self, commit=True):
        from django.contrib.auth.hashers import make_password
        if not commit:
            user = super().save(commit=False)
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            return user

        hashed_pwd = make_password(self.cleaned_data['password1'])
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO auth_user
                        (username, email, first_name, last_name, password,
                         is_superuser, is_staff, is_active, date_joined)
                    VALUES (%s, %s, %s, %s, %s, FALSE, FALSE, TRUE, CURRENT_TIMESTAMP)
                    RETURNING id
                """, [
                    self.cleaned_data['username'], self.cleaned_data['email'],
                    self.cleaned_data['first_name'], self.cleaned_data['last_name'],
                    hashed_pwd,
                ])
                user_id = cursor.fetchone()[0]

                cursor.execute("SELECT member_id FROM auth_system_member ORDER BY id DESC LIMIT 1")
                last = cursor.fetchone()
                if last:
                    try:
                        next_num = int(last[0].replace('AMS', '')) + 1
                    except (ValueError, AttributeError):
                        next_num = 1
                else:
                    next_num = 1
                member_id_val = f"AMS{next_num:06d}"

                cursor.execute("""
                    INSERT INTO auth_system_member
                        (user_id, member_id, salutation, country_code, phone_number,
                         nationality, total_miles, award_miles, is_active,
                         created_at, updated_at)
                    VALUES (%s, %s, 'mr', '+62', %s, 'Indonesia', 0, 0, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, [user_id, member_id_val, self.cleaned_data.get('phone_number', '')])
        except DatabaseError as e:
            raise forms.ValidationError(_extract_trigger_msg(e))
        return User.objects.get(pk=user_id)

    def clean_email(self):
        return self.cleaned_data.get('email')

    def clean_first_name(self):
        return _sanitize_text(self.cleaned_data.get('first_name'), max_length=50)

    def clean_last_name(self):
        return _sanitize_text(self.cleaned_data.get('last_name'), max_length=50)

    def clean_phone_number(self):
        return _sanitize_phone(self.cleaned_data.get('phone_number'))


class StaffMemberUpdateForm(forms.Form):
    """Form untuk staff memperbarui data member."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nama Depan'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nama Belakang'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nomor HP'
        })
    )

    def __init__(self, *args, **kwargs):
        self.member = kwargs.pop('member', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if _email_exists(email, exclude_user_id=self.member.user.pk):
            raise forms.ValidationError('Email sudah digunakan.')
        return email

    def clean_first_name(self):
        return _sanitize_text(self.cleaned_data.get('first_name'), max_length=50)

    def clean_last_name(self):
        return _sanitize_text(self.cleaned_data.get('last_name'), max_length=50)

    def clean_phone_number(self):
        return _sanitize_phone(self.cleaned_data.get('phone_number'))

    def save(self):
        user = self.member.user
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE auth_user
                SET email=%s, first_name=%s, last_name=%s
                WHERE id=%s
            """, [
                self.cleaned_data['email'],
                self.cleaned_data['first_name'],
                self.cleaned_data['last_name'],
                user.id
            ])
            cursor.execute("""
                UPDATE auth_system_member
                SET phone_number=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
            """, [
                self.cleaned_data['phone_number'],
                self.member.id
            ])
        return self.member


class StaffRegistrationForm(UserCreationForm):
    """Form untuk registrasi Staff"""
    username = forms.CharField(required=False, widget=forms.HiddenInput())
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    salutation = forms.ChoiceField(
        choices=[('', 'Pilih')] + Staff.SALUTATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    first_name = forms.CharField(
        max_length=50,
        label='Nama Depan-Tengah',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nama depan-tengah'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nama Belakang'
        })
    )
    country_code = forms.ChoiceField(
        choices=COUNTRY_CODE_CHOICES,
        initial='+62',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nomor Telepon'
        })
    )
    birth_date = forms.DateField(
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    nationality = forms.ChoiceField(
        choices=[('', 'Pilih negara')] + NATIONALITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    maskapai = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _ensure_default_maskapai()
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Konfirmasi Password'})
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, code, name FROM auth_system_maskapai WHERE is_active = TRUE ORDER BY name"
            )
            mks = cursor.fetchall()
        self.fields['maskapai'].choices = [('', 'Pilih maskapai')] + [
            (str(r[0]), f"{r[1]} - {r[2]}") for r in mks
        ]

    def save(self, commit=True):
        from django.contrib.auth.hashers import make_password
        if not commit:
            user = super().save(commit=False)
            user.username = self.cleaned_data['username']
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            return user

        hashed_pwd = make_password(self.cleaned_data['password1'])
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO auth_user
                        (username, email, first_name, last_name, password,
                         is_superuser, is_staff, is_active, date_joined)
                    VALUES (%s, %s, %s, %s, %s, FALSE, FALSE, TRUE, CURRENT_TIMESTAMP)
                    RETURNING id
                """, [
                    self.cleaned_data['username'], self.cleaned_data['email'],
                    self.cleaned_data['first_name'], self.cleaned_data['last_name'],
                    hashed_pwd,
                ])
                user_id = cursor.fetchone()[0]

                cursor.execute("SELECT staff_id FROM auth_system_staff ORDER BY id DESC LIMIT 1")
                last = cursor.fetchone()
                if last:
                    try:
                        next_num = int(last[0].replace('STF', '')) + 1
                    except (ValueError, AttributeError):
                        next_num = 1
                else:
                    next_num = 1
                staff_id = f"STF{next_num:06d}"

                cursor.execute("""
                    INSERT INTO auth_system_staff
                        (user_id, staff_id, salutation, country_code, phone_number,
                         birth_date, nationality, maskapai_id, department, is_active,
                         created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, [
                    user_id, staff_id, self.cleaned_data['salutation'],
                    self.cleaned_data['country_code'], self.cleaned_data['phone_number'],
                    self.cleaned_data['birth_date'], self.cleaned_data['nationality'],
                    self.cleaned_data['maskapai'] or None, 'operations',
                ])
        except DatabaseError as e:
            raise forms.ValidationError(_extract_trigger_msg(e))
        return User.objects.get(pk=user_id)

    def clean_username(self):
        return _build_unique_username(self.cleaned_data.get('email', ''))

    def clean_first_name(self):
        return _sanitize_text(self.cleaned_data.get('first_name'), max_length=50)

    def clean_last_name(self):
        return _sanitize_text(self.cleaned_data.get('last_name'), max_length=50)

    def clean_phone_number(self):
        return _sanitize_phone(self.cleaned_data.get('phone_number'))

    def clean_birth_date(self):
        value = self.cleaned_data.get('birth_date')
        if value and value > date.today():
            raise forms.ValidationError('Tanggal lahir tidak valid.')
        return value

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError('Email harus diisi.')
        return email

    def clean_maskapai(self):
        maskapai = self.cleaned_data.get('maskapai')
        if not maskapai:
            raise forms.ValidationError('Maskapai wajib dipilih.')
        return maskapai


class BaseProfileSettingsForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        required=False,
        disabled=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    salutation = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-select'}))
    first_name = forms.CharField(
        max_length=50,
        label='Nama Depan / Tengah',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama depan / tengah'})
    )
    last_name = forms.CharField(
        max_length=50,
        label='Nama Belakang',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama belakang'})
    )
    country_code = forms.ChoiceField(
        choices=COUNTRY_CODE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone_number = forms.CharField(
        max_length=20,
        label='Nomor HP',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nomor HP'})
    )
    nationality = forms.ChoiceField(
        choices=[('', 'Pilih negara')] + NATIONALITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    birth_date = forms.DateField(
        label='Tanggal Lahir',
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    salutation_choices = []

    def __init__(self, *args, user, profile, **kwargs):
        self.user = user
        self.profile = profile
        super().__init__(*args, **kwargs)
        self.fields['salutation'].choices = [('', 'Pilih')] + list(self.salutation_choices)
        self.fields['email'].initial = user.email
        self.fields['salutation'].initial = profile.salutation
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['country_code'].initial = profile.country_code
        self.fields['phone_number'].initial = profile.phone_number
        self.fields['nationality'].initial = profile.nationality
        self.fields['birth_date'].initial = profile.birth_date

    def clean_first_name(self):
        return _sanitize_text(self.cleaned_data.get('first_name'), max_length=50)

    def clean_last_name(self):
        return _sanitize_text(self.cleaned_data.get('last_name'), max_length=50)

    def clean_phone_number(self):
        return _sanitize_phone(self.cleaned_data.get('phone_number'))

    def clean_birth_date(self):
        value = self.cleaned_data.get('birth_date')
        if value and value > date.today():
            raise forms.ValidationError('Tanggal lahir tidak valid.')
        return value

    def save(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE auth_user
                SET first_name=%s, last_name=%s
                WHERE id=%s
            """, [
                self.cleaned_data['first_name'],
                self.cleaned_data['last_name'],
                self.user.id
            ])
        # Update user object in memory just in case
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']

        self.profile.salutation = self.cleaned_data['salutation']
        self.profile.country_code = self.cleaned_data['country_code']
        self.profile.phone_number = self.cleaned_data['phone_number']
        self.profile.nationality = self.cleaned_data['nationality']
        self.profile.birth_date = self.cleaned_data['birth_date']
        self._save_profile()
        return self.user, self.profile

    def _save_profile(self):
        raise NotImplementedError


class MemberProfileSettingsForm(BaseProfileSettingsForm):
    member_id = forms.CharField(
        label='Nomor Member',
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    joined_at = forms.DateField(
        label='Tanggal Bergabung',
        required=False,
        disabled=True,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    salutation_choices = Member.SALUTATION_CHOICES

    def __init__(self, *args, user, profile, **kwargs):
        super().__init__(*args, user=user, profile=profile, **kwargs)
        self.fields['member_id'].initial = profile.member_id
        self.fields['joined_at'].initial = profile.created_at.date() if profile.created_at else None
        self.order_fields([
            'email', 'member_id', 'joined_at', 'salutation',
            'first_name', 'last_name', 'nationality',
            'country_code', 'phone_number', 'birth_date',
        ])

    def _save_profile(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE auth_system_member
                SET salutation=%s, country_code=%s, phone_number=%s,
                    nationality=%s, birth_date=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
            """, [
                self.cleaned_data['salutation'],
                self.cleaned_data['country_code'],
                self.cleaned_data['phone_number'],
                self.cleaned_data['nationality'],
                self.cleaned_data['birth_date'],
                self.profile.id,
            ])


class StaffProfileSettingsForm(BaseProfileSettingsForm):
    staff_id = forms.CharField(
        label='ID Staff',
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    maskapai = forms.ChoiceField(
        label='Kode Maskapai',
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    salutation_choices = Staff.SALUTATION_CHOICES

    def __init__(self, *args, user, profile, **kwargs):
        super().__init__(*args, user=user, profile=profile, **kwargs)
        _ensure_default_maskapai()
        self.fields['staff_id'].initial = profile.staff_id
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, code, name FROM auth_system_maskapai
                   WHERE is_active = TRUE OR id = %s ORDER BY name""",
                [profile.maskapai_id or 0]
            )
            mks = cursor.fetchall()
        self.fields['maskapai'].choices = [('', 'Pilih maskapai')] + [
            (str(r[0]), f"{r[1]} - {r[2]}") for r in mks
        ]
        self.fields['maskapai'].initial = str(profile.maskapai_id) if profile.maskapai_id else ''
        self.order_fields([
            'email', 'staff_id', 'salutation',
            'first_name', 'last_name', 'nationality',
            'country_code', 'phone_number', 'birth_date', 'maskapai',
        ])

    def clean_maskapai(self):
        maskapai_id = self.cleaned_data.get('maskapai')
        if not maskapai_id:
            raise forms.ValidationError('Maskapai wajib dipilih.')
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT is_active FROM auth_system_maskapai WHERE id = %s",
                [maskapai_id]
            )
            row = cursor.fetchone()
        if not row:
            raise forms.ValidationError('Maskapai tidak ditemukan.')
        if not row[0]:
            raise forms.ValidationError('Maskapai tidak aktif.')
        return maskapai_id

    def _save_profile(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE auth_system_staff
                   SET salutation=%s, country_code=%s, phone_number=%s,
                       nationality=%s, birth_date=%s, maskapai_id=%s, updated_at=CURRENT_TIMESTAMP
                   WHERE id=%s""",
                [
                    self.cleaned_data['salutation'],
                    self.cleaned_data['country_code'],
                    self.cleaned_data['phone_number'],
                    self.cleaned_data['nationality'],
                    self.cleaned_data['birth_date'],
                    self.cleaned_data['maskapai'],
                    self.profile.id,
                ]
            )


class StyledPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label='Password Lama',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'})
    )
    new_password1 = forms.CharField(
        label='Password Baru',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'})
    )
    new_password2 = forms.CharField(
        label='Konfirmasi Password Baru',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'})
    )


class ClaimMissingMilesForm(forms.Form):
    """Form untuk member membuat dan mengubah claim missing miles."""

    maskapai = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    bandara_asal = forms.ChoiceField(
        choices=[],
        label='Bandara Asal',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    bandara_tujuan = forms.ChoiceField(
        choices=[],
        label='Bandara Tujuan',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    kelas_kabin = forms.ChoiceField(
        choices=[('', 'Pilih kelas')] + ClaimMissingMiles.KABIN_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    pnr = forms.CharField(
        max_length=20,
        required=False,
        label='PNR',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Passenger Name Record'}),
    )
    flight_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: GA123'}),
    )
    ticket_number = forms.CharField(
        max_length=50,
        required=False,
        label='Nomor Tiket',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nomor tiket'}),
    )
    flight_date = forms.DateField(
        label='Tanggal Penerbangan',
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Alasan claim'}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Keterangan tambahan (opsional)'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, code, name FROM auth_system_maskapai WHERE is_active = TRUE ORDER BY name"
            )
            mks = cursor.fetchall()
            cursor.execute(
                "SELECT iata_code, nama FROM auth_system_bandara ORDER BY iata_code"
            )
            bds = cursor.fetchall()
        self.fields['maskapai'].choices = [('', 'Pilih maskapai')] + [
            (str(r[0]), f"{r[1]} - {r[2]}") for r in mks
        ]
        bandara_choices = [('', 'Pilih bandara')] + [(r[0], f"{r[0]} - {r[1]}") for r in bds]
        self.fields['bandara_asal'].choices = bandara_choices
        self.fields['bandara_tujuan'].choices = bandara_choices

    def clean_flight_number(self):
        flight_number = _sanitize_text(self.cleaned_data.get('flight_number'), max_length=20).upper()
        if not re.fullmatch(r"[A-Z0-9\-]+", flight_number):
            raise forms.ValidationError('Format nomor flight tidak valid.')
        return flight_number

    def clean_ticket_number(self):
        ticket_number = self.cleaned_data.get('ticket_number', '').strip()
        return _sanitize_text(ticket_number, max_length=50) if ticket_number else ''

    def clean_pnr(self):
        return _sanitize_text(self.cleaned_data.get('pnr'), max_length=20).upper()

    def clean_reason(self):
        return _sanitize_text(self.cleaned_data.get('reason'), max_length=500)

    def clean_description(self):
        return _sanitize_text(self.cleaned_data.get('description'), max_length=500)


class StaffClaimUpdateForm(forms.Form):
    """Form untuk staff membaca dan mengubah status claim."""

    status = forms.ChoiceField(
        choices=ClaimMissingMiles.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    miles_amount = forms.IntegerField(
        min_value=1,
        required=False,
        label='Jumlah Miles',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Isi saat approve'}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Catatan staff'}),
    )

    def __init__(self, *args, claim=None, **kwargs):
        self.claim = claim
        super().__init__(*args, **kwargs)
        if claim and not self.is_bound:
            self.fields['status'].initial = claim.status
            self.fields['miles_amount'].initial = claim.miles_amount
            self.fields['description'].initial = claim.description

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('status')
        miles_amount = cleaned.get('miles_amount')
        if status == 'approved' and not miles_amount:
            self.add_error('miles_amount', 'Jumlah miles wajib diisi saat menyetujui claim.')
        return cleaned

    def clean_description(self):
        return _sanitize_text(self.cleaned_data.get('description'), max_length=500)


class TransferMilesForm(forms.Form):
    """Form transfer miles antar member."""

    email_penerima = forms.EmailField(
        label='Email Member Penerima',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email member tujuan'})
    )
    miles_amount = forms.IntegerField(
        label='Jumlah Miles',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    description = forms.CharField(
        label='Keterangan',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Keterangan transfer (opsional)'})
    )

    def __init__(self, *args, **kwargs):
        self.from_member = kwargs.pop('from_member')
        super().__init__(*args, **kwargs)
        self.to_member = None

    def clean_email_penerima(self):
        from types import SimpleNamespace
        email = self.cleaned_data['email_penerima'].strip().lower()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT m.id, m.user_id, m.member_id, m.award_miles
                FROM auth_system_member m
                JOIN auth_user u ON u.id = m.user_id
                WHERE LOWER(u.email) = LOWER(%s) AND m.is_active = TRUE
            """, [email])
            row = cursor.fetchone()
        if row is None:
            raise forms.ValidationError('Email tidak ditemukan atau member tidak aktif.')

        self.to_member = SimpleNamespace(
            id=row[0], user_id=row[1], member_id=row[2], award_miles=row[3],
        )
        if self.to_member.id == self.from_member.id:
            raise forms.ValidationError('Tidak bisa transfer ke akun sendiri.')

        return email

    def clean_description(self):
        return _sanitize_text(self.cleaned_data.get('description'), max_length=500)


class StaffManageMemberCreateForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama depan'})
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama belakang'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Konfirmasi password'})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nomor HP'})
    )

    def clean_first_name(self):
        return _sanitize_text(self.cleaned_data.get('first_name'), max_length=50)

    def clean_last_name(self):
        return _sanitize_text(self.cleaned_data.get('last_name'), max_length=50)

    def clean_username(self):
        username = _sanitize_text(self.cleaned_data.get('username'), max_length=150)
        if _username_exists(username):
            raise forms.ValidationError('Username sudah digunakan.')
        return username

    def clean_email(self):
        return self.cleaned_data.get('email')

    def clean_phone_number(self):
        return _sanitize_phone(self.cleaned_data.get('phone_number'))

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Konfirmasi password tidak cocok.')
        return cleaned

    def save(self):
        from django.contrib.auth.hashers import make_password
        from types import SimpleNamespace
        hashed_pwd = make_password(self.cleaned_data['password1'])
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO auth_user
                        (username, email, first_name, last_name, password,
                         is_superuser, is_staff, is_active, date_joined)
                    VALUES (%s, %s, %s, %s, %s, FALSE, FALSE, TRUE, CURRENT_TIMESTAMP)
                    RETURNING id
                """, [
                    self.cleaned_data['username'], self.cleaned_data['email'],
                    self.cleaned_data['first_name'], self.cleaned_data['last_name'],
                    hashed_pwd,
                ])
                user_id = cursor.fetchone()[0]

                cursor.execute("SELECT member_id FROM auth_system_member ORDER BY id DESC LIMIT 1")
                last = cursor.fetchone()
                if last:
                    try:
                        next_num = int(last[0].replace('AMS', '')) + 1
                    except (ValueError, AttributeError):
                        next_num = 1
                else:
                    next_num = 1
                member_id_val = f"AMS{next_num:06d}"

                cursor.execute("""
                    INSERT INTO auth_system_member
                        (user_id, member_id, salutation, country_code, phone_number,
                         nationality, total_miles, award_miles, is_active,
                         created_at, updated_at)
                    VALUES (%s, %s, 'mr', '+62', %s, 'Indonesia', 0, 0, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                """, [user_id, member_id_val, self.cleaned_data['phone_number']])
                member_pk = cursor.fetchone()[0]
        except DatabaseError as e:
            raise forms.ValidationError(_extract_trigger_msg(e))
        user = User.objects.get(pk=user_id)
        member = SimpleNamespace(id=member_pk, member_id=member_id_val, user=user)
        return user, member


class StaffManageMemberUpdateForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama depan'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama belakang'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nomor HP'})
    )
    tier = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, member, **kwargs):
        self.member = member
        super().__init__(*args, **kwargs)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, tier_name FROM auth_system_tier
                WHERE is_active = TRUE ORDER BY minimal_tier_miles
            """)
            tier_rows = cursor.fetchall()
        self.fields['tier'].choices = [('', '-- Tidak Ubah Tier --')] + [
            (str(r[0]), dict(self._tier_label_map()).get(r[1], r[1])) for r in tier_rows
        ]

        if not self.is_bound:
            self.fields['first_name'].initial = member.user.first_name
            self.fields['last_name'].initial = member.user.last_name
            self.fields['email'].initial = member.user.email
            self.fields['phone_number'].initial = member.phone_number
            self.fields['tier'].initial = str(member.tier_id) if member.tier_id else ''

    @staticmethod
    def _tier_label_map():
        return [('bronze', 'Bronze'), ('silver', 'Silver'),
                ('gold', 'Gold'), ('platinum', 'Platinum')]

    def clean_first_name(self):
        return _sanitize_text(self.cleaned_data.get('first_name'), max_length=50)

    def clean_last_name(self):
        return _sanitize_text(self.cleaned_data.get('last_name'), max_length=50)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM auth_user WHERE LOWER(email) = LOWER(%s) AND id <> %s LIMIT 1",
                [email, self.member.user_id]
            )
            if cursor.fetchone():
                raise forms.ValidationError('Email sudah digunakan.')
        return email

    def clean_phone_number(self):
        return _sanitize_phone(self.cleaned_data.get('phone_number'))

    def save(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE auth_user SET first_name = %s, last_name = %s, email = %s
                WHERE id = %s
            """, [
                self.cleaned_data['first_name'],
                self.cleaned_data['last_name'],
                self.cleaned_data['email'],
                self.member.user_id,
            ])

            tier_id = self.cleaned_data.get('tier') or None
            if tier_id:
                cursor.execute("""
                    UPDATE auth_system_member
                    SET phone_number = %s, tier_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, [self.cleaned_data['phone_number'], tier_id, self.member.id])
            else:
                cursor.execute("""
                    UPDATE auth_system_member
                    SET phone_number = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, [self.cleaned_data['phone_number'], self.member.id])
        return self.member


class IdentityForm(forms.ModelForm):
    class Meta:
        model = Identity
        fields = ('document_number', 'document_type', 'country', 'issue_date', 'expiry_date')
        widgets = {
            'document_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nomor dokumen'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_document_number(self):
        return _sanitize_text(self.cleaned_data.get('document_number'), max_length=100)

    def clean(self):
        cleaned = super().clean()
        issue_date = cleaned.get('issue_date')
        expiry_date = cleaned.get('expiry_date')
        if issue_date and expiry_date and expiry_date <= issue_date:
            self.add_error('expiry_date', 'Tanggal habis harus lebih besar dari tanggal terbit.')
        return cleaned


def _generate_kode_hadiah():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT kode_hadiah FROM auth_system_hadiah WHERE kode_hadiah LIKE 'RWD-%' ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
    if row:
        try:
            last_number = int(row[0].split('-')[-1])
        except (TypeError, ValueError):
            last_number = 0
    else:
        last_number = 0
    return f"RWD-{last_number + 1:03d}"


class HadiahForm(forms.Form):
    """Form untuk membuat/mengedit Hadiah"""

    kode_hadiah = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kode hadiah akan digenerate otomatis',
            'maxlength': '20',
        }),
    )
    nama_hadiah = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nama Hadiah',
            'maxlength': '100',
        }),
    )
    penyedia = forms.ChoiceField(
        label='Penyedia',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    miles_diperlukan = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Miles dibutuhkan',
            'min': '1',
        }),
    )
    deskripsi = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Deskripsi hadiah',
            'rows': 3,
        }),
    )
    tanggal_valid_mulai = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    tanggal_valid_akhir = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def __init__(self, *args, hadiah_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._hadiah_id = hadiah_id

        _ensure_default_penyedia()
        _ensure_default_mitra()

        with connection.cursor() as cursor:
            if hadiah_id:
                cursor.execute("""
                    SELECT DISTINCT p.id, p.name
                    FROM auth_system_penyedia p
                    WHERE p.is_active = TRUE
                       OR p.id = (SELECT penyedia_id FROM auth_system_hadiah WHERE id = %s)
                    ORDER BY p.name
                """, [hadiah_id])
            else:
                cursor.execute(
                    "SELECT id, name FROM auth_system_penyedia WHERE is_active = TRUE ORDER BY name"
                )
            rows = cursor.fetchall()

        self.fields['penyedia'].choices = [('', 'Pilih penyedia')] + [
            (str(r[0]), r[1]) for r in rows
        ]

        if hadiah_id:
            self.fields['kode_hadiah'].disabled = True
            self.fields['kode_hadiah'].help_text = 'Kode hadiah tidak dapat diubah.'
        else:
            self.fields['kode_hadiah'].initial = _generate_kode_hadiah()
            self.fields['kode_hadiah'].widget.attrs['readonly'] = True

    def clean_kode_hadiah(self):
        if self._hadiah_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT kode_hadiah FROM auth_system_hadiah WHERE id = %s", [self._hadiah_id]
                )
                row = cursor.fetchone()
            return row[0] if row else ''
        kode = _sanitize_text(self.cleaned_data.get('kode_hadiah'), max_length=20)
        return (kode.upper() if kode else None) or _generate_kode_hadiah()

    def clean_nama_hadiah(self):
        return _sanitize_text(self.cleaned_data.get('nama_hadiah'), max_length=100)

    def clean_deskripsi(self):
        return _sanitize_text(self.cleaned_data.get('deskripsi'), max_length=500)

    def clean_miles_diperlukan(self):
        miles = self.cleaned_data.get('miles_diperlukan')
        if miles is not None and miles <= 0:
            raise forms.ValidationError('Miles dibutuhkan harus lebih dari 0.')
        return miles

    def clean(self):
        cleaned = super().clean()
        tanggal_mulai = cleaned.get('tanggal_valid_mulai')
        tanggal_akhir = cleaned.get('tanggal_valid_akhir')

        if tanggal_mulai and tanggal_akhir and tanggal_akhir < tanggal_mulai:
            self.add_error('tanggal_valid_akhir', 'Tanggal akhir harus lebih besar atau sama dengan tanggal mulai.')

        if not self._hadiah_id and tanggal_mulai and tanggal_mulai < date.today():
            self.add_error('tanggal_valid_mulai', 'Tanggal mulai tidak boleh di masa lalu.')

        return cleaned

    def save(self):
        from types import SimpleNamespace
        d = self.cleaned_data
        penyedia_id = int(d['penyedia']) if d.get('penyedia') else None

        with connection.cursor() as cursor:
            if self._hadiah_id:
                cursor.execute("""
                    UPDATE auth_system_hadiah
                    SET nama_hadiah = %s, penyedia_id = %s, miles_diperlukan = %s,
                        deskripsi = %s, tanggal_valid_mulai = %s, tanggal_valid_akhir = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, kode_hadiah, nama_hadiah
                """, [
                    d['nama_hadiah'], penyedia_id, d['miles_diperlukan'],
                    d.get('deskripsi') or '', d['tanggal_valid_mulai'],
                    d['tanggal_valid_akhir'], self._hadiah_id,
                ])
            else:
                cursor.execute("""
                    INSERT INTO auth_system_hadiah
                        (kode_hadiah, nama_hadiah, penyedia_id, miles_diperlukan,
                         deskripsi, tanggal_valid_mulai, tanggal_valid_akhir,
                         status, jumlah_tersedia, jumlah_terjual, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id, kode_hadiah, nama_hadiah
                """, [
                    d['kode_hadiah'], d['nama_hadiah'], penyedia_id, d['miles_diperlukan'],
                    d.get('deskripsi') or '', d['tanggal_valid_mulai'], d['tanggal_valid_akhir'],
                ])
            row = cursor.fetchone()

        return SimpleNamespace(id=row[0], kode_hadiah=row[1], nama_hadiah=row[2])


class MitraForm(forms.Form):
    """Form untuk membuat / mengedit Mitra."""

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama mitra'}),
    )
    code = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kode unik (maks 10 karakter)'}),
    )
    contact_person = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama contact person (opsional)'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nomor telepon (opsional)'}),
    )
    tanggal_kerja_sama = forms.DateField(
        required=False,
        label='Tanggal Kerja Sama',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, mitra=None, **kwargs):
        self.mitra = mitra
        super().__init__(*args, **kwargs)
        if mitra and not self.is_bound:
            self.fields['name'].initial = mitra.name
            self.fields['code'].initial = mitra.code
            self.fields['contact_person'].initial = mitra.contact_person
            self.fields['email'].initial = mitra.email
            self.fields['phone_number'].initial = mitra.phone_number
            self.fields['tanggal_kerja_sama'].initial = mitra.tanggal_kerja_sama
            self.fields['is_active'].initial = mitra.is_active

    def clean_name(self):
        return _sanitize_text(self.cleaned_data.get('name'), max_length=100)

    def clean_code(self):
        code = _sanitize_text(self.cleaned_data.get('code'), max_length=10).upper()
        sql = "SELECT 1 FROM auth_system_mitra WHERE LOWER(code) = LOWER(%s)"
        params = [code]
        if self.mitra:
            sql += " AND id <> %s"
            params.append(self.mitra.id)
        sql += " LIMIT 1"
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            if cursor.fetchone():
                raise forms.ValidationError('Kode mitra sudah digunakan.')
        return code

    def clean_phone_number(self):
        return _sanitize_phone(self.cleaned_data.get('phone_number'))
