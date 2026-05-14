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


class Tier(models.Model):
    """Model untuk Tier Member AeroMiles"""
    TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    
    tier_name = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    minimal_tier_miles = models.BigIntegerField(help_text="Minimum miles required for this tier")
    minimal_frekuensi_terbang = models.IntegerField(help_text="Minimum flight frequency for this tier")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_tier_name_display()}"
    
    class Meta:
        verbose_name = 'Tier'
        verbose_name_plural = 'Tiers'
        ordering = ['minimal_tier_miles']


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
    award_miles = models.BigIntegerField(default=0, help_text="Miles available for redeeming rewards")
    tier = models.ForeignKey(Tier, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
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
    tanggal_kerja_sama = models.DateField(null=True, blank=True)
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

    KABIN_CHOICES = [
        ('economy', 'Economy'),
        ('business', 'Business'),
        ('first', 'First Class'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='missing_miles_claims')
    claim_id = models.CharField(max_length=50, unique=True)
    maskapai = models.ForeignKey('Maskapai', on_delete=models.SET_NULL, null=True, blank=True, related_name='claims')
    bandara_asal = models.ForeignKey('Bandara', on_delete=models.SET_NULL, null=True, blank=True, related_name='claims_asal')
    bandara_tujuan = models.ForeignKey('Bandara', on_delete=models.SET_NULL, null=True, blank=True, related_name='claims_tujuan')
    kelas_kabin = models.CharField(max_length=10, choices=KABIN_CHOICES, blank=True, null=True)
    pnr = models.CharField(max_length=20, blank=True, null=True)
    flight_number = models.CharField(max_length=20)
    ticket_number = models.CharField(max_length=50, blank=True, null=True)
    flight_date = models.DateField()
    miles_amount = models.BigIntegerField(null=True, blank=True)
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


class Bandara(models.Model):
    iata_code = models.CharField(max_length=3, primary_key=True)
    nama = models.CharField(max_length=100)
    kota = models.CharField(max_length=100)
    negara = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.iata_code} - {self.nama} ({self.kota})"

    class Meta:
        verbose_name = 'Bandara'
        verbose_name_plural = 'Bandara'
        ordering = ['iata_code']


class AwardMilesPackage(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    harga_paket = models.DecimalField(max_digits=15, decimal_places=2)
    jumlah_award_miles = models.IntegerField()

    @staticmethod
    def generate_id():
        last = AwardMilesPackage.objects.order_by('id').last()
        if last:
            try:
                num = int(last.id.split('-')[1])
            except (IndexError, ValueError):
                num = 0
        else:
            num = 0
        return f"AMP-{num + 1:03d}"

    def __str__(self):
        return f"{self.id} - {self.jumlah_award_miles:,} miles @ Rp {self.harga_paket:,.0f}"

    class Meta:
        verbose_name = 'Award Miles Package'
        verbose_name_plural = 'Award Miles Packages'
        ordering = ['jumlah_award_miles']


class MemberAwardMilesPackage(models.Model):
    """Riwayat pembelian paket award miles oleh member"""
    award_miles_package = models.ForeignKey(AwardMilesPackage, on_delete=models.PROTECT, related_name='purchases')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='package_purchases')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member} - {self.award_miles_package} @ {self.timestamp}"

    class Meta:
        verbose_name = 'Member Award Miles Package'
        verbose_name_plural = 'Member Award Miles Packages'
        ordering = ['-timestamp']


class Hadiah(models.Model):
    """Model untuk Hadiah (Gift/Prize) dalam program AeroMiles"""
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('inactive', 'Tidak Aktif'),
        ('discontinued', 'Dihentikan'),
    ]

    kode_hadiah = models.CharField(max_length=20, unique=True)
    nama_hadiah = models.CharField(max_length=100)
    deskripsi = models.TextField(blank=True, null=True)
    penyedia = models.ForeignKey(Penyedia, on_delete=models.CASCADE, related_name='hadiah_list')
    mitra = models.ForeignKey(Mitra, on_delete=models.SET_NULL, null=True, blank=True, related_name='hadiah_list')
    miles_diperlukan = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    tanggal_valid_mulai = models.DateField()
    tanggal_valid_akhir = models.DateField()
    jumlah_tersedia = models.IntegerField(default=0)
    jumlah_terjual = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def generate_kode_hadiah():
        """Generate kode hadiah berurutan dengan format RWD-001."""
        last_hadiah = Hadiah.objects.order_by('-id').first()
        if last_hadiah and last_hadiah.kode_hadiah.startswith('RWD-'):
            try:
                last_number = int(last_hadiah.kode_hadiah.split('-')[-1])
            except (TypeError, ValueError):
                last_number = 0
        else:
            last_number = 0
        return f"RWD-{last_number + 1:03d}"

    def __str__(self):
        return f"{self.kode_hadiah} - {self.nama_hadiah}"

    @property
    def sisa_hadiah(self):
        """Menghitung sisa hadiah yang tersedia"""
        return self.jumlah_tersedia - self.jumlah_terjual

    @property
    def is_periode_valid(self):
        """Mengecek apakah periode hadiah masih berlaku"""
        from datetime import date
        today = date.today()
        return self.tanggal_valid_mulai <= today <= self.tanggal_valid_akhir

    @property
    def sudah_kadaluarsa(self):
        from datetime import date
        return self.tanggal_valid_akhir < date.today()

    class Meta:
        verbose_name = 'Hadiah'
        verbose_name_plural = 'Hadiah'
        ordering = ['-created_at']


class Redeem(models.Model):
    """Riwayat penukaran hadiah oleh member menggunakan award miles"""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='redeems')
    hadiah = models.ForeignKey(Hadiah, on_delete=models.PROTECT, related_name='redeems')
    timestamp = models.DateTimeField(auto_now_add=True)
    miles_used = models.BigIntegerField()

    def __str__(self):
        return f"{self.member} - {self.hadiah} @ {self.timestamp}"

    class Meta:
        verbose_name = 'Redeem'
        verbose_name_plural = 'Redeems'
        ordering = ['-timestamp']
