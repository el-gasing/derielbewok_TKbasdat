from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import ClaimMissingMiles, Member, Staff


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


class MemberRegistrationForm(UserCreationForm):
    """Form untuk registrasi Member"""
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
            'placeholder': 'Nomor Telepon'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Konfirmasi Password'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create associated Member profile with auto-generated member_id
            Member.objects.create(
                user=user,
                member_id=Member.generate_member_id(),
                phone_number=self.cleaned_data.get('phone_number', '')
            )
        
        return user


class StaffRegistrationForm(UserCreationForm):
    """Form untuk registrasi Staff"""
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
            'placeholder': 'Nomor Telepon'
        })
    )
    department = forms.ChoiceField(
        choices=Staff._meta.get_field('department').choices,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Konfirmasi Password'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create associated Staff profile with auto-generated staff_id
            Staff.objects.create(
                user=user,
                staff_id=Staff.generate_staff_id(),
                phone_number=self.cleaned_data.get('phone_number', ''),
                department=self.cleaned_data['department']
            )
        
        return user


class ClaimMissingMilesForm(forms.ModelForm):
    """Form untuk member membuat dan mengubah claim missing miles."""

    class Meta:
        model = ClaimMissingMiles
        fields = ('flight_number', 'flight_date', 'miles_amount', 'reason', 'description')
        widgets = {
            'flight_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: GA123'}),
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


class StaffClaimUpdateForm(forms.ModelForm):
    """Form untuk staff membaca dan mengubah status claim."""

    class Meta:
        model = ClaimMissingMiles
        fields = ('status', 'description')
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Catatan staff'}),
        }


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
        to_member_id = self.cleaned_data['to_member_id']
        try:
            self.to_member = Member.objects.get(member_id=to_member_id, is_active=True)
        except Member.DoesNotExist as exc:
            raise forms.ValidationError('ID Member tujuan tidak ditemukan atau tidak aktif.') from exc

        if self.to_member.id == self.from_member.id:
            raise forms.ValidationError('Tidak bisa transfer ke akun sendiri.')

        return to_member_id

    def clean(self):
        cleaned_data = super().clean()
        miles_amount = cleaned_data.get('miles_amount')
        if miles_amount and self.from_member.total_miles < miles_amount:
            self.add_error('miles_amount', 'Total miles tidak mencukupi untuk transfer ini.')
        return cleaned_data
