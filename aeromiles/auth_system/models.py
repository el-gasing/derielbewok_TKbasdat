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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    member_id = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    total_miles = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.member_id}"
    
    class Meta:
        verbose_name = 'Member'
        verbose_name_plural = 'Members'


class Staff(models.Model):
    """Model untuk Staff AeroMiles"""
    DEPARTMENT_CHOICES = [
        ('customer_service', 'Customer Service'),
        ('operations', 'Operations'),
        ('finance', 'Finance'),
        ('marketing', 'Marketing'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    staff_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.staff_id}"
    
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
