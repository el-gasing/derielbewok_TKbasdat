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
        ('mr', 'Mr'),
        ('mrs', 'Mrs'),
        ('ms', 'Ms'),
        ('dr', 'Dr'),
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
        """Generate unique member ID dengan format AMS + 6 digit number"""
        last_member = Member.objects.all().order_by('id').last()
        if last_member:
            last_num = int(last_member.member_id.replace('AMS', ''))
            new_num = last_num + 1
        else:
            new_num = 1
        return f"AMS{new_num:06d}"
    
    class Meta:
        verbose_name = 'Member'
        verbose_name_plural = 'Members'


class Staff(models.Model):
    """Model untuk Staff AeroMiles"""
    SALUTATION_CHOICES = Member.SALUTATION_CHOICES

    DEPARTMENT_CHOICES = [
        ('customer_service', 'Customer Service'),
        ('operations', 'Operations'),
        ('finance', 'Finance'),
        ('marketing', 'Marketing'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    staff_id = models.CharField(max_length=50, unique=True)
    salutation = models.CharField(max_length=10, choices=SALUTATION_CHOICES, default='mr')
    country_code = models.CharField(max_length=6, default='+62')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, default='Indonesia')
    maskapai = models.ForeignKey('Maskapai', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_members')
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES, default='admin')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.staff_id}"
    
    @staticmethod
    def generate_staff_id():
        """Generate unique staff ID dengan format STF + 6 digit number"""
        last_staff = Staff.objects.all().order_by('id').last()
        if last_staff:
            last_num = int(last_staff.staff_id.replace('STF', ''))
            new_num = last_num + 1
        else:
            new_num = 1
        return f"STF{new_num:06d}"
    
    class Meta:
        verbose_name = 'Staff'
        verbose_name_plural = 'Staff Members'


class Maskapai(models.Model):
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


class ClaimMissingMiles(models.Model):
    """Model untuk Claim Missing Miles"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    ]
    
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
    
    def __str__(self):
        return f"{self.claim_id} - {self.member}"
    
    class Meta:
        verbose_name = 'Claim Missing Miles'
        verbose_name_plural = 'Claim Missing Miles'


class TransferMiles(models.Model):
    """Model untuk Transfer Miles antar Member"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    from_member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transfer_from')
    to_member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transfer_to')
    transfer_id = models.CharField(max_length=50, unique=True)
    miles_amount = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.transfer_id}: {self.from_member} -> {self.to_member}"
    
    class Meta:
        verbose_name = 'Transfer Miles'
        verbose_name_plural = 'Transfer Miles'


class Identity(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('passport', 'Passport'),
        ('ktp', 'KTP'),
        ('sim', 'SIM'),
        ('other', 'Lainnya'),
    ]

    COUNTRY_CHOICES = [
        ('ID', 'Indonesia'),
        ('SG', 'Singapura'),
        ('MY', 'Malaysia'),
        ('TH', 'Thailand'),
        ('PH', 'Filipina'),
        ('VN', 'Vietnam'),
        ('TW', 'Taiwan'),
        ('HK', 'Hong Kong'),
        ('KR', 'Korea'),
        ('JP', 'Jepang'),
        ('CN', 'China'),
        ('AU', 'Australia'),
        ('NZ', 'New Zealand'),
        ('US', 'Amerika Serikat'),
        ('UK', 'Inggris'),
        ('DE', 'Jerman'),
        ('FR', 'Prancis'),
        ('IT', 'Italia'),
        ('ES', 'Spanyol'),
        ('NL', 'Belanda'),
        ('CH', 'Swiss'),
        ('AT', 'Austria'),
        ('SE', 'Swedia'),
        ('NO', 'Norwegia'),
        ('DK', 'Denmark'),
        ('FI', 'Finlandia'),
        ('PL', 'Polandia'),
        ('CZ', 'Czech'),
        ('GR', 'Yunani'),
        ('PT', 'Portugis'),
        ('BE', 'Belgia'),
        ('BR', 'Brazil'),
        ('MX', 'Meksiko'),
        ('CA', 'Kanada'),
        ('IN', 'India'),
        ('PK', 'Pakistan'),
        ('BD', 'Bangladesh'),
        ('AE', 'UAE'),
        ('SA', 'Arab Saudi'),
        ('QA', 'Qatar'),
        ('KW', 'Kuwait'),
        ('EG', 'Mesir'),
        ('ZA', 'Afrika Selatan'),
        ('NG', 'Nigeria'),
        ('KE', 'Kenya'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='identities')
    document_number = models.CharField(max_length=100)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    is_expired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.member} - {self.document_number}"

    class Meta:
        verbose_name = 'Identity'
        verbose_name_plural = 'Identities'
        unique_together = (('member', 'document_number'),)
