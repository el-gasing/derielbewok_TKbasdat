import re
from datetime import date

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.db.models import Q
from django.utils.html import strip_tags
from django.db import connection
from .models import Bandara, ClaimMissingMiles, Identity, Maskapai, Member, Staff, Hadiah, Penyedia, Mitra


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


def _build_unique_username(email):
    base = (email or '').split('@')[0]
    base = re.sub(r'[^a-zA-Z0-9_.-]', '', base).lower() or 'user'
    username = base[:150]
    suffix = 1

    while User.objects.filter(username=username).exists():
        extra = str(suffix)
        username = f"{base[:max(1, 150 - len(extra))]}{extra}"
        suffix += 1

    return username


def _ensure_default_maskapai():
    """Pastikan dropdown maskapai punya opsi dasar saat database masih kosong."""
    if Maskapai.objects.exists():
        return

    for item in DEFAULT_MASKAPAI:
        Maskapai.objects.get_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'email': f"{item['code'].lower()}@aeromiles.local",
                'is_active': True,
            },
        )


def _ensure_default_penyedia():
    if Penyedia.objects.exists():
        return

    for item in DEFAULT_PENYEDIA:
        Penyedia.objects.get_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'email': f"{item['code'].lower()}@aeromiles.local",
                'is_active': True,
            },
        )


def _ensure_default_mitra():
    if Mitra.objects.exists():
        return

    for item in DEFAULT_MITRA:
        Mitra.objects.get_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'email': f"{item['code'].lower()}@aeromiles.local",
                'is_active': True,
            },
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
        
        # Cek apakah input adalah email (ada @)
        if '@' in username_input:
            try:
                user = User.objects.get(email__iexact=username_input)
                return user.username
            except User.DoesNotExist:
                raise forms.ValidationError('Email tidak terdaftar.')
            except User.MultipleObjectsReturned:
                # Fallback: cari yang paling baru
                user = User.objects.filter(email__iexact=username_input).order_by('-last_login').first()
                if user:
                    return user.username
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
        user = super().save(commit=False)
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
            # Create associated Member profile with auto-generated member_id
            Member.objects.create(
                user=user,
                member_id=Member.generate_member_id(),
                salutation=self.cleaned_data['salutation'],
                country_code=self.cleaned_data['country_code'],
                phone_number=self.cleaned_data['phone_number'],
                birth_date=self.cleaned_data['birth_date'],
                nationality=self.cleaned_data['nationality']
            )

        return user

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
        """Ensure email is unique for member registration"""
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError('Email harus diisi.')
        
        # Check if email already exists
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user:
            raise forms.ValidationError('Email ini sudah terdaftar. Gunakan email lain atau login dengan akun yang ada.')
        
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
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            Member.objects.create(
                user=user,
                member_id=Member.generate_member_id(),
                country_code='+62',
                phone_number=self.cleaned_data.get('phone_number', ''),
            )
        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email sudah digunakan.')
        return email

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
        if User.objects.filter(email__iexact=email).exclude(pk=self.member.user.pk).exists():
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
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save(update_fields=['email', 'first_name', 'last_name'])
        self.member.phone_number = self.cleaned_data['phone_number']
        self.member.save(update_fields=['phone_number'])
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
    maskapai = forms.ModelChoiceField(
        queryset=Maskapai.objects.none(),
        empty_label='Pilih maskapai',
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
        self.fields['maskapai'].queryset = Maskapai.objects.filter(is_active=True).order_by('name')
        self.fields['maskapai'].label_from_instance = lambda obj: f"{obj.code} - {obj.name}"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
            # Create associated Staff profile with auto-generated staff_id
            Staff.objects.create(
                user=user,
                staff_id=Staff.generate_staff_id(),
                salutation=self.cleaned_data['salutation'],
                country_code=self.cleaned_data['country_code'],
                phone_number=self.cleaned_data['phone_number'],
                birth_date=self.cleaned_data['birth_date'],
                nationality=self.cleaned_data['nationality'],
                maskapai=self.cleaned_data['maskapai'],
                department='operations'
            )

        return user

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
        """Ensure email is unique for staff registration"""
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError('Email harus diisi.')
        
        # Check if email already exists
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user:
            raise forms.ValidationError('Email ini sudah terdaftar. Gunakan email lain atau login dengan akun yang ada.')
        
        return email

    def clean_maskapai(self):
        maskapai = self.cleaned_data.get('maskapai')
        if not maskapai:
            raise forms.ValidationError('Maskapai wajib dipilih.')
        if not maskapai.is_active:
            raise forms.ValidationError('Maskapai tidak aktif.')
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
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.save(update_fields=['first_name', 'last_name'])

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
        self.profile.save(update_fields=[
            'salutation', 'country_code', 'phone_number', 'nationality', 'birth_date', 'updated_at'
        ])


class StaffProfileSettingsForm(BaseProfileSettingsForm):
    staff_id = forms.CharField(
        label='ID Staff',
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    maskapai = forms.ModelChoiceField(
        label='Kode Maskapai',
        queryset=Maskapai.objects.none(),
        empty_label='Pilih maskapai',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    salutation_choices = Staff.SALUTATION_CHOICES

    def __init__(self, *args, user, profile, **kwargs):
        super().__init__(*args, user=user, profile=profile, **kwargs)
        _ensure_default_maskapai()
        self.fields['staff_id'].initial = profile.staff_id
        maskapai_filter = Q(is_active=True)
        if profile.maskapai_id:
            maskapai_filter |= Q(pk=profile.maskapai_id)
        self.fields['maskapai'].queryset = Maskapai.objects.filter(maskapai_filter).order_by('name')
        self.fields['maskapai'].label_from_instance = lambda obj: f"{obj.code} - {obj.name}"
        self.fields['maskapai'].initial = profile.maskapai
        self.order_fields([
            'email', 'staff_id', 'salutation',
            'first_name', 'last_name', 'nationality',
            'country_code', 'phone_number', 'birth_date', 'maskapai',
        ])

    def clean_maskapai(self):
        maskapai = self.cleaned_data.get('maskapai')
        if not maskapai:
            raise forms.ValidationError('Maskapai wajib dipilih.')
        if not maskapai.is_active:
            raise forms.ValidationError('Maskapai tidak aktif.')
        return maskapai

    def _save_profile(self):
        self.profile.maskapai = self.cleaned_data['maskapai']
        self.profile.save(update_fields=[
            'salutation', 'country_code', 'phone_number', 'nationality', 'birth_date', 'maskapai', 'updated_at'
        ])


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

    maskapai = forms.ModelChoiceField(
        queryset=Maskapai.objects.none(),
        empty_label='Pilih maskapai',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    bandara_asal = forms.ModelChoiceField(
        queryset=Bandara.objects.none(),
        label='Bandara Asal',
        empty_label='Pilih bandara asal',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    bandara_tujuan = forms.ModelChoiceField(
        queryset=Bandara.objects.none(),
        label='Bandara Tujuan',
        empty_label='Pilih bandara tujuan',
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
        self.fields['maskapai'].queryset = Maskapai.objects.filter(is_active=True).order_by('name')
        self.fields['maskapai'].label_from_instance = lambda obj: f"{obj.code} - {obj.name}"
        self.fields['bandara_asal'].queryset = Bandara.objects.all().order_by('iata_code')
        self.fields['bandara_asal'].label_from_instance = lambda obj: f"{obj.iata_code} - {obj.nama}"
        self.fields['bandara_tujuan'].queryset = Bandara.objects.all().order_by('iata_code')
        self.fields['bandara_tujuan'].label_from_instance = lambda obj: f"{obj.iata_code} - {obj.nama}"

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
        email = self.cleaned_data['email_penerima'].strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
            self.to_member = Member.objects.get(user=user, is_active=True)
        except (User.DoesNotExist, Member.DoesNotExist) as exc:
            raise forms.ValidationError('Email tidak ditemukan atau member tidak aktif.') from exc

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
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username sudah digunakan.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email sudah digunakan.')
        return email

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
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
        )
        member = Member.objects.create(
            user=user,
            member_id=Member.generate_member_id(),
            phone_number=self.cleaned_data['phone_number'],
        )
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
                    SET phone_number = %s, tier_id = %s, updated_at = NOW()
                    WHERE id = %s
                """, [self.cleaned_data['phone_number'], tier_id, self.member.id])
            else:
                cursor.execute("""
                    UPDATE auth_system_member
                    SET phone_number = %s, updated_at = NOW()
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


class HadiahForm(forms.ModelForm):
    """Form untuk membuat/mengedit Hadiah"""

    class Meta:
        model = Hadiah
        fields = (
            'kode_hadiah',
            'nama_hadiah',
            'penyedia',
            'miles_diperlukan',
            'deskripsi',
            'tanggal_valid_mulai',
            'tanggal_valid_akhir',
        )
        widgets = {
            'kode_hadiah': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kode hadiah akan digenerate otomatis',
                'maxlength': '20'
            }),
            'nama_hadiah': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nama Hadiah',
                'maxlength': '100'
            }),
            'deskripsi': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Deskripsi hadiah',
                'rows': 3
            }),
            'penyedia': forms.Select(attrs={'class': 'form-select'}),
            'miles_diperlukan': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Miles dibutuhkan',
                'min': '1'
            }),
            'tanggal_valid_mulai': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'tanggal_valid_akhir': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _ensure_default_penyedia()
        _ensure_default_mitra()

        penyedia_filter = Q(is_active=True)
        if self.instance and self.instance.pk:
            if self.instance.penyedia_id:
                penyedia_filter |= Q(pk=self.instance.penyedia_id)

        self.fields['penyedia'].queryset = Penyedia.objects.filter(penyedia_filter).order_by('name')
        self.fields['penyedia'].empty_label = 'Pilih penyedia'
        self.fields['penyedia'].label_from_instance = lambda obj: obj.name

        if self.instance and self.instance.pk:
            self.fields['kode_hadiah'].disabled = True
            self.fields['kode_hadiah'].help_text = 'Kode hadiah tidak dapat diubah.'
        else:
            self.fields['kode_hadiah'].required = False
            self.fields['kode_hadiah'].initial = Hadiah.generate_kode_hadiah()
            self.fields['kode_hadiah'].widget.attrs['readonly'] = True

    def clean_kode_hadiah(self):
        if self.instance and self.instance.pk:
            return self.instance.kode_hadiah

        kode = _sanitize_text(self.cleaned_data.get('kode_hadiah'), max_length=20).upper()
        return kode or Hadiah.generate_kode_hadiah()

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

        if not self.instance.pk and tanggal_mulai and tanggal_mulai < date.today():
            self.add_error('tanggal_valid_mulai', 'Tanggal mulai tidak boleh di masa lalu.')

        return cleaned

    def save(self, commit=True):
        hadiah = super().save(commit=False)
        if not hadiah.status:
            hadiah.status = 'active'
        if not hadiah.jumlah_tersedia:
            hadiah.jumlah_tersedia = 1
        if commit:
            hadiah.save()
        return hadiah


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
        qs = Mitra.objects.filter(code__iexact=code)
        if self.mitra:
            qs = qs.exclude(pk=self.mitra.pk)
        if qs.exists():
            raise forms.ValidationError('Kode mitra sudah digunakan.')
        return code

    def clean_phone_number(self):
        return _sanitize_phone(self.cleaned_data.get('phone_number'))
