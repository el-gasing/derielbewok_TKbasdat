# Troubleshooting: Staff Registration Account Disappearance

## Problem Summary
Staff account adalah "ilang" (disappears) setelah registrasi - dapat dibuat tapi tidak dapat login kemudian.

## Background: Testing & Findings
Semua test yang kami jalankan menunjukkan sistem bekerja dengan baik:
- ✓ Database user creation works
- ✓ Form validation works
- ✓ Staff profile creation works
- ✓ Login works
- ✓ Web interface registration works (via Django test client)

## Step-by-Step Troubleshooting

### 1. BASIC: Check Database Directly
Jalankan command ini untuk lihat apakah user benar-benar tersimpan:

```bash
python manage.py shell
```

Di dalam shell:
```python
from django.contrib.auth.models import User
from auth_system.models import Staff

# Check total users and staff
print("Total users:", User.objects.count())
print("Total staff:", Staff.objects.count())

# List recent users
for u in User.objects.order_by('-id')[:10]:
    print(f"  {u.id}: {u.username} ({u.email})")

# Check if your test staff user exists
u = User.objects.filter(email='YOUREMAIL@domain.com').first()
if u:
    print(f"✓ User found: {u.username}")
    staff = Staff.objects.filter(user=u).exists()
    print(f"✓ Staff profile exists: {staff}")
else:
    print("✗ User NOT found in database")
```

### 2. CHECK: Form Validation Errors
Kali ini form mungkin menunjukkan error yang tidak terlihat. Cek di halaman registrasi:
- Apakah ada pesan error merah di bawah field-field?
- Scroll ke bawah untuk lihat semua error
- Khususnya cek:
  - Salutation field (harus dipilih dari dropdown)
  - Email (harus format valid dan unik)
  - Maskapai (harus dipilih)
  - Password (harus cocok confirmation-nya)

### 3. RUN: Debug Script
Jalankan script untuk trace step-by-step:

```bash
python debug_staff_registration.py
```

Script ini akan membuat akun test dan show dimana error terjadi jika ada.

### 4. CHECK: Browser Logs
Buka browser Developer Tools (F12), tab Console:
- Ada error message?
- Ada warning?
- Apakah form benar-benar di-submit? (check Network tab untuk POST request)

### 5. TEST: Manual Database Creation
Kalau script work tapi web form tidak, ada issue pada form/view. Test dengan:

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from auth_system.models import Maskapai, Staff
from datetime import date

# Get maskapai
m = Maskapai.objects.first()

# Create user manually
user = User.objects.create_user(
    username='manual_test_staff',
    email='manual_staff@test.com',
    password='TestPass123!',
    first_name='Manual',
    last_name='Test'
)
print(f"User created: {user.id}")

# Create staff profile
staff = Staff.objects.create(
    user=user,
    staff_id=Staff.generate_staff_id(),
    salutation='mr',
    country_code='+62',
    phone_number='081234567890',
    birth_date=date(1990, 1, 1),
    nationality='Indonesia',
    maskapai=m,
    department='operations'
)
print(f"Staff created: {staff.staff_id}")

# Try to login
user_check = User.objects.get(username='manual_test_staff')
password_check = user_check.check_password('TestPass123!')
print(f"Login possible: {password_check}")
```

### 6. DIAGNOSE: Check Django Logs
Kalau ada ERROR atau WARNING di terminal Django, itu indikasi masalah:

Jalankan development server dengan verbose output:
```bash
python manage.py runserver --verbosity 2
```

Kemudian coba registrasi dan lihat terminal untuk error messages.

### 7. CLEAR: Database & Try Fresh
Kalau masih gagal, coba reset database:

```bash
python manage.py migrate --fake auth_system zero
python manage.py migrate auth_system
python manage.py init_tiers
```

Kemudian coba registrasi lagi.

## What to Provide for Debugging
Kalau masih tidak work setelah semua di atas, provide:

1. **Screenshot dari:**
   - Form yang diisi (show semua field)
   - Error message yang muncul (jika ada)
   - Browser console (F12 → Console tab)

2. **Output dari:**
   - `python debug_staff_registration.py` (full output)
   - Database query: `python manage.py shell` → `User.objects.count()`, `Staff.objects.count()`

3. **Describe:**
   - Exactly apa yang terjadi step-by-step (mulai dari klik apa)
   - Setelah register, klik apa? Apakah redirect ke dashboard?
   - Terus kemudian coba login apakah tidak bisa find account?

## Quick Checklist
- [ ] Jalankan `debug_staff_registration.py` - apakah semua test PASS?
- [ ] Cek browser console (F12) - ada error?
- [ ] Cek form field - ada error message?
- [ ] Cek database langsung (shell) - user ada atau tidak?
- [ ] Apakah Django development server show error message di terminal?

---

## Technical Background (untuk referensi)

### Registration Flow
```
1. User akses /auth/register/staff/
2. Form GET → render template
3. User isi form dan POST
4. View: form.is_valid() - validasi field
5. View: form.save() - create User + Staff profile
6. View: login(request, user) - authenticate
7. View: redirect to dashboard
8. Django session save ke browser
```

### Possible Failure Points
- Form validation fails (user ditunjukkan error message)
- User.save() fails (internal DB error)
- Staff.objects.create() fails (foreign key error, unique constraint, etc)
- login() fails (rare, tapi bisa karena session DB issue)
- Database connection issue (Django tidak bisa connect ke DB)

### Database Schema Relevant
- `auth_user` table: username, email harus UNIQUE
- `auth_system_staff` table: user FK reference ke auth_user (CASCADE delete)
- Session data: stored di `django_session` table

---

Kalau sudah jalankan semua langkah di atas dan masih tidak work, share outputnya dan kita debug lebih lanjut.
