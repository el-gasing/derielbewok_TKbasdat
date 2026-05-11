import re
from datetime import date

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.html import strip_tags
from .models import ClaimMissingMiles, Identity, Maskapai, Member, Staff


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
        username = self.cleaned_data.get('username', '').strip()
        if '@' in username:
            user = User.objects.filter(email__iexact=username).first()
            if user:
                return user.username
        return username


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

    def clean_maskapai(self):
        maskapai = self.cleaned_data.get('maskapai')
        if not maskapai:
            raise forms.ValidationError('Maskapai wajib dipilih.')
        if not maskapai.is_active:
            raise forms.ValidationError('Maskapai tidak aktif.')
        return maskapai


class ClaimMissingMilesForm(forms.ModelForm):
    """Form untuk member membuat dan mengubah claim missing miles."""

    class Meta:
        model = ClaimMissingMiles
        fields = ('flight_number', 'ticket_number', 'flight_date', 'miles_amount', 'reason', 'description')
        widgets = {
            'flight_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: GA123'}),
            'ticket_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nomor tiket'}),
            'flight_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'miles_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Alasan claim'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Keterangan tambahan (opsional)'}),
        }

    def clean_miles_amount(self):
        miles_amount = self.cleaned_data['miles_amount']
        if miles_amount <= 0:
            raise forms.ValidationError('Jumlah miles harus lebih dari 0.')
        return miles_amount

    def clean_flight_number(self):
        flight_number = _sanitize_text(self.cleaned_data.get('flight_number'), max_length=20).upper()
        if not re.fullmatch(r"[A-Z0-9\-]+", flight_number):
            raise forms.ValidationError('Format nomor flight tidak valid.')
        return flight_number

    def clean_ticket_number(self):
        ticket_number = self.cleaned_data.get('ticket_number', '').strip()
        if ticket_number:
            return _sanitize_text(ticket_number, max_length=50)
        return ticket_number

    def clean_reason(self):
        return _sanitize_text(self.cleaned_data.get('reason'), max_length=500)

    def clean_description(self):
        return _sanitize_text(self.cleaned_data.get('description'), max_length=500)


class StaffClaimUpdateForm(forms.ModelForm):
    """Form untuk staff membaca dan mengubah status claim."""

    class Meta:
        model = ClaimMissingMiles
        fields = ('status', 'description')
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Catatan staff'}),
        }

    def clean_description(self):
        return _sanitize_text(self.cleaned_data.get('description'), max_length=500)


class TransferMilesForm(forms.Form):
    """Form transfer miles antar member."""

    to_member_id = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan ID Member tujuan'})
    )
    miles_amount = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Keterangan transfer (opsional)'})
    )

    def __init__(self, *args, **kwargs):
        self.from_member = kwargs.pop('from_member')
        super().__init__(*args, **kwargs)
        self.to_member = None

    def clean_to_member_id(self):
        to_member_id = _sanitize_text(self.cleaned_data['to_member_id'], max_length=50).upper()
        try:
            self.to_member = Member.objects.get(member_id=to_member_id, is_active=True)
        except Member.DoesNotExist as exc:
            raise forms.ValidationError('ID Member tujuan tidak ditemukan atau tidak aktif.') from exc

        if self.to_member.id == self.from_member.id:
            raise forms.ValidationError('Tidak bisa transfer ke akun sendiri.')

        return to_member_id

    def clean_description(self):
        return _sanitize_text(self.cleaned_data.get('description'), max_length=500)

    def clean(self):
        cleaned_data = super().clean()
        miles_amount = cleaned_data.get('miles_amount')
        if miles_amount and self.from_member.total_miles < miles_amount:
            self.add_error('miles_amount', 'Total miles tidak mencukupi untuk transfer ini.')
        return cleaned_data


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
