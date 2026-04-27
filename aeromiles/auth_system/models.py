from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator

class UserRole(models.Model):
    """Model untuk menyimpan role pengguna"""
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('staff', 'Staff'),
        ('maskapai', 'Maskapai'),
        ('penyedia', 'Penyedia'),
        ('mitra', 'Mitra'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.get_role_display()
    
    class Meta:
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

class Member(models.Model):
    """Model untuk Member AeroMiles"""
    SALUTATION_CHOICES = [
        ('mr', 'Mr'), ('mrs', 'Mrs'), ('ms', 'Ms'), ('dr', 'Dr'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    member_id = models.CharField(max_length=50, unique=True)
    salutation = models.CharField(max_length=10, choices=SALUTATION_CHOICES, default='mr')
    country_code = models.CharField(max_length=6, default='+62')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, default='Indonesia')
    total_miles = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.member_id}"
    
    @staticmethod
    def generate_member_id():
        last_member = Member.objects.all().order_by('id').last()
        if last_member:
            last_num = int(last_member.member_id.replace('AMS', ''))
            new_num = last_num + 1
        else:
            new_num = 1
        return f"AMS{new_num:06d}"

class Staff(models.Model):
    """Model untuk Staff AeroMiles"""
    SALUTATION_CHOICES = Member.SALUTATION_CHOICES
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    staff_id = models.CharField(max_length=50, unique=True)
    salutation = models.CharField(max_length=10, choices=SALUTATION_CHOICES, default='mr')
    country_code = models.CharField(max_length=6, default='+62')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, default='Indonesia')
    maskapai = models.ForeignKey('Maskapai', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_members')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.staff_id}"

class Identity(models.Model):
    """Model untuk Identitas Member (Pasport, KTP, SIM, dll)"""
    DOCUMENT_TYPE_CHOICES = [('passport', 'Passport'), ('ktp', 'KTP'), ('sim', 'SIM'), ('other', 'Lainnya')]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='identities')
    document_number = models.CharField(max_length=100, unique=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    country = models.CharField(max_length=80) # Using simple string for flexibility
    issue_date = models.DateField()
    expiry_date = models.DateField()
    is_expired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def check_expiry(self):
        from datetime import date
        self.is_expired = self.expiry_date < date.today()
        return self.is_expired

class ClaimMissingMiles(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('processed', 'Processed')]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='missing_miles_claims')
    claim_id = models.CharField(max_length=50, unique=True)
    flight_number = models.CharField(max_length=20)
    flight_date = models.DateField()
    miles_amount = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField()
    description = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_claims')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TransferMiles(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
    from_member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transfer_from')
    to_member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transfer_to')
    transfer_id = models.CharField(max_length=50, unique=True)
    miles_amount = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Maskapai(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    email = models.EmailField(validators=[EmailValidator()])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name

    """Model untuk Maskapai (Airline)"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(validators=[EmailValidator()])
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Maskapai'
        verbose_name_plural = 'Maskapai'


class Penyedia(models.Model):
    """Model untuk Penyedia (Provider)"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(validators=[EmailValidator()])
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Penyedia'
        verbose_name_plural = 'Penyedia'


class Mitra(models.Model):
    """Model untuk Mitra (Partnership)"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(validators=[EmailValidator()])
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Mitra'
        verbose_name_plural = 'Mitra'