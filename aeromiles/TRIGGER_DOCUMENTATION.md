# AeroMiles - Trigger Implementation Documentation

## Overview
Sistem AeroMiles mengimplementasikan 4 trigger utama untuk validasi data dan business logic automation:
1. **Trigger 1**: Pemeriksaan Duplikasi Email saat Registrasi
2. **Trigger 2**: Verifikasi Kredensial saat Login  
3. **Trigger 4**: Pemeriksaan Duplikasi Klaim Missing Miles
4. **Trigger 5**: Auto-Update Member Tier

---

## Trigger 1: Pemeriksaan Duplikasi Email saat Registrasi

### Requirement
Ketika pengguna melakukan registrasi akun baru, sistem otomatis akan memeriksa apakah email yang sama sudah terdaftar sebelumnya pada tabel PENGGUNA. Jika sudah ada, sistem akan membatalkan proses pendaftaran.

### Implementasi

#### Backend (Django ORM)
**File**: `auth_system/forms.py`
```python
def clean_email(self):
    """Ensure email is unique"""
    email = self.cleaned_data.get('email', '').strip()
    if not email:
        raise forms.ValidationError('Email harus diisi.')
    
    # Check if email already exists (case-insensitive)
    existing_user = User.objects.filter(email__iexact=email).first()
    if existing_user:
        raise forms.ValidationError('Email ini sudah terdaftar. Gunakan email lain atau login dengan akun yang ada.')
    
    return email
```

#### PostgreSQL Trigger
**File**: `sql/TK04_Trigger_A_14/TK04_Trigger_1_2_4_Derriel_Rabiul_Bewok.sql`

```sql
CREATE OR REPLACE FUNCTION fn_check_duplicate_email()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if email already exists (case-insensitive)
    IF EXISTS (
        SELECT 1 FROM auth_user
        WHERE LOWER(email) = LOWER(NEW.email)
          AND id != COALESCE(NEW.id, 0)
    ) THEN
        RAISE EXCEPTION 'ERROR: Email "%" sudah terdaftar, silakan gunakan email lain.', NEW.email;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER TR_CHECK_DUPLICATE_EMAIL
BEFORE INSERT OR UPDATE ON auth_user
FOR EACH ROW
EXECUTE FUNCTION fn_check_duplicate_email();
```

### Error Message
```
ERROR: Email "<email>" sudah terdaftar, silakan gunakan email lain.
```

### Catatan
- Validasi adalah **case-insensitive**: `users@gmail.com` dan `USERS@gmail.COM` dianggap sama
- Berlaku untuk REGISTRASI dan UPDATE email
- SQLite: Validasi via Django ORM di aplikasi
- PostgreSQL: Validasi via trigger di database

### Test Case
```
Skenario 1: Registrasi dengan email baru ✓
- Email: user@gmail.com
- Hasil: Akun berhasil dibuat

Skenario 2: Registrasi dengan email yang sudah ada ✗
- Email: user@gmail.com (sudah terdaftar)
- Hasil: Error ditampilkan, akun tidak dibuat

Skenario 3: Case-insensitive check ✗
- Email 1: USER@gmail.com (sudah ada)
- Email 2: user@gmail.com (registrasi baru)
- Hasil: Error ditampilkan, duplikasi terdeteksi
```

---

## Trigger 2: Verifikasi Kredensial saat Login

### Requirement
Ketika pengguna melakukan login, sistem akan memverifikasi apakah kombinasi email dan password yang dimasukkan sesuai dengan data yang tersimpan di database. Jika kredensial tidak cocok, sistem akan menolak akses.

### Implementasi

#### Backend (Django ORM)
**File**: `auth_system/forms.py`
```python
class LoginForm(AuthenticationForm):
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
        
        return username_input
```

#### PostgreSQL Stored Procedure
**File**: `sql/TK04_Trigger_A_14/TK04_Trigger_1_2_4_Derriel_Rabiul_Bewok.sql`

```sql
CREATE OR REPLACE FUNCTION sp_verify_login_credentials(
    p_email VARCHAR,
    p_password VARCHAR
)
RETURNS TABLE (
    user_id BIGINT,
    username VARCHAR,
    email VARCHAR,
    is_active BOOLEAN,
    is_staff BOOLEAN,
    login_status VARCHAR
) AS $$
BEGIN
    -- Check if email exists
    IF NOT EXISTS (SELECT 1 FROM auth_user WHERE LOWER(email) = LOWER(p_email)) THEN
        RETURN QUERY SELECT 
            0::BIGINT, ''::VARCHAR, p_email::VARCHAR, FALSE::BOOLEAN, 
            FALSE::BOOLEAN, 'ERROR: Email atau password salah, silakan coba lagi.'::VARCHAR;
        RETURN;
    END IF;
    
    -- Return user info for successful email match
    -- Note: Password validation done by Django ORM (bcrypt hashing)
    RETURN QUERY SELECT 
        u.id, u.username, u.email, u.is_active,
        (SELECT COUNT(*) > 0 FROM auth_system_staff WHERE user_id = u.id)::BOOLEAN,
        'PENDING'::VARCHAR
    FROM auth_user u
    WHERE LOWER(u.email) = LOWER(p_email)
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;
```

### Error Message
```
ERROR: Email atau password salah, silakan coba lagi.
```

### Flow Login
1. User input email/username + password
2. Django LoginForm validate email existence
3. Password checked via bcrypt (ORM level)
4. Redirect ke dashboard jika berhasil
5. Error message jika gagal

### Catatan
- Password verification dilakukan di aplikasi (Django ORM) karena menggunakan bcrypt hash
- Trigger ini lebih sebagai validation layer di PostgreSQL
- Mendukung login via **email** atau **username**

### Test Case
```
Skenario 1: Login dengan email dan password benar ✓
- Email: user@gmail.com
- Password: SecurePass123
- Hasil: Redirect ke dashboard

Skenario 2: Login dengan email salah ✗
- Email: invalid@gmail.com
- Password: SecurePass123
- Hasil: Error "Email atau password salah"

Skenario 3: Login dengan password salah ✗
- Email: user@gmail.com
- Password: WrongPassword
- Hasil: Error "Email atau password salah"

Skenario 4: Login dengan username ✓
- Username: user3
- Password: SecurePass123
- Hasil: Redirect ke dashboard
```

---

## Trigger 4: Pemeriksaan Duplikasi Klaim Missing Miles

### Requirement
Mencegah anggota mengirimkan klaim ganda untuk penerbangan yang sama dengan nomor tiket yang sama.

### Implementasi

#### Backend (Django ORM)
**File**: `auth_system/services.py`
```python
def check_duplicate_claim(member, flight_number, ticket_number, flight_date, exclude_claim_id=None):
    """Check if similar claim already exists"""
    query = ClaimMissingMiles.objects.filter(
        member=member,
        flight_number__iexact=flight_number,
        ticket_number__iexact=ticket_number or '',
        flight_date=flight_date
    )
    if exclude_claim_id:
        query = query.exclude(id=exclude_claim_id)
    return query.exists()
```

#### PostgreSQL Trigger
**File**: `sql/TK04_Trigger_A_14/TK04_Trigger_1_2_4_Derriel_Rabiul_Bewok.sql`

```sql
CREATE TRIGGER TR_CHECK_DUPLICATE_MISSING_MILES_CLAIMS
BEFORE INSERT OR UPDATE ON auth_system_claimmissingmiles
FOR EACH ROW
EXECUTE FUNCTION fn_check_duplicate_missing_miles_claims();
```

### Error Message
```
ERROR: Klaim untuk penerbangan "<flight_number>" pada tanggal "<flight_date>" 
dengan nomor tiket "<ticket_number>" sudah pernah diajukan sebelumnya.
```

### Validasi Kombinasi
Kombinasi yang dicek:
- Flight Number (case-insensitive)
- Flight Date (exact match)
- Ticket Number (case-insensitive)
- Member Email (case-insensitive)

---

## Trigger 5: Auto-Update Member Tier

### Requirement
Otomatis upgrade tier member berdasarkan total miles yang dikumpulkan.

### Implementasi

#### Backend (Django ORM)
**File**: `auth_system/services.py`
```python
def update_member_tier(member):
    """Automatically update member tier based on total miles"""
    total_miles = ClaimMissingMiles.objects.filter(
        member=member,
        status='approved'
    ).aggregate(Sum('miles'))['miles__sum'] or 0
    
    tier = Tier.objects.filter(
        minimal_tier_miles__lte=total_miles,
        is_active=True
    ).order_by('-minimal_tier_miles').first()
    
    if tier:
        member.tier = tier
        member.save()
```

#### PostgreSQL Trigger
Trigger akan otomatis dijalankan ketika status claim berubah menjadi "approved".

### Tier Levels
- Bronze: 0 - 5000 miles
- Silver: 5001 - 15000 miles
- Gold: 15001 - 50000 miles
- Platinum: 50001+ miles

---

## Deployment

### Untuk PostgreSQL Production
1. Apply trigger SQL:
```bash
psql -U postgres -d aeromiles_db -f sql/TK04_Trigger_A_14/TK04_Trigger_1_2_4_Derriel_Rabiul_Bewok.sql
```

2. Verify triggers:
```sql
SELECT trigger_name FROM information_schema.triggers WHERE trigger_schema = 'public';
```

### Untuk SQLite Development
- Semua validasi dilakukan di level Django ORM
- File: `auth_system/forms.py` dan `auth_system/services.py`
- Management command: `python manage.py init_tiers`

---

## Testing

### Test Database Constraints
```python
python manage.py shell
```

```python
from django.contrib.auth.models import User
from auth_system.models import Member, Staff, ClaimMissingMiles

# Test Trigger 1: Duplicate Email
user1 = User.objects.create_user('test1', 'test@gmail.com', 'pass')
try:
    user2 = User.objects.create_user('test2', 'test@gmail.com', 'pass')  # Should fail
except Exception as e:
    print(f"Trigger 1 blocked: {e}")

# Test Trigger 4: Duplicate Claim
claim1 = ClaimMissingMiles.objects.create(
    member=member, flight_number='GA123', 
    ticket_number='TK001', flight_date='2026-05-14'
)
try:
    claim2 = ClaimMissingMiles.objects.create(
        member=member, flight_number='GA123', 
        ticket_number='TK001', flight_date='2026-05-14'
    )  # Should fail
except Exception as e:
    print(f"Trigger 4 blocked: {e}")
```

---

## References
- Django Forms Validation: `auth_system/forms.py`
- Backend Services: `auth_system/services.py`
- PostgreSQL Triggers: `sql/TK04_Trigger_A_14/TK04_Trigger_1_2_4_Derriel_Rabiul_Bewok.sql`
- Models: `auth_system/models.py`
