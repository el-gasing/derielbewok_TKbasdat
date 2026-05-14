#!/usr/bin/env python
"""
Debug script untuk trace staff registration problem.
Run: python debug_staff_registration.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aeromiles.settings')
django.setup()

from django.contrib.auth.models import User
from auth_system.models import Staff, Maskapai
from auth_system.forms import StaffRegistrationForm
from datetime import date

def test_registration():
    print("=" * 60)
    print("DEBUG: Staff Registration Test")
    print("=" * 60)
    
    # Step 1: Check database state before
    print("\n[STEP 1] Checking database state BEFORE registration...")
    users_before = User.objects.count()
    staff_before = Staff.objects.count()
    print(f"  Users in DB: {users_before}")
    print(f"  Staff profiles in DB: {staff_before}")
    
    # Step 2: Get maskapai
    print("\n[STEP 2] Getting maskapai...")
    maskapai = Maskapai.objects.first()
    if not maskapai:
        print("  ERROR: No maskapai found! Creating default...")
        maskapai = Maskapai.objects.create(
            code='GA',
            name='Garuda Indonesia',
            email='ga@aeromiles.local',
            is_active=True
        )
    print(f"  Maskapai: {maskapai.code} - {maskapai.name}")
    
    # Step 3: Create test data
    print("\n[STEP 3] Preparing form data...")
    import time
    test_email = f'debug_staff_test_{int(time.time())}@aeromiles.com'
    form_data = {
        'username': '',  # Let it auto-generate
        'email': test_email,
        'first_name': 'Debug',
        'last_name': 'Test',
        'password1': 'DebugPass123!',
        'password2': 'DebugPass123!',
        'salutation': 'mr',
        'country_code': '+62',
        'phone_number': '081234567890',
        'birth_date': '1990-01-01',
        'nationality': 'Indonesia',
        'maskapai': maskapai.id
    }
    print(f"  Test email: {test_email}")
    print(f"  Form data prepared: {len(form_data)} fields")
    
    # Step 4: Create form and validate
    print("\n[STEP 4] Creating form and validating...")
    form = StaffRegistrationForm(form_data)
    is_valid = form.is_valid()
    print(f"  Form is_valid: {is_valid}")
    
    if not is_valid:
        print("  ERROR: Form validation failed!")
        for field, errors in form.errors.items():
            print(f"    {field}: {errors}")
        return False
    
    # Step 5: Save form
    print("\n[STEP 5] Calling form.save()...")
    try:
        user = form.save()
        print(f"  SUCCESS: form.save() returned user object")
        print(f"    User ID: {user.id}")
        print(f"    Username: {user.username}")
        print(f"    Email: {user.email}")
    except Exception as e:
        print(f"  ERROR during form.save(): {type(e).__name__}: {e}")
        return False
    
    # Step 6: Verify user in database
    print("\n[STEP 6] Verifying user in database...")
    try:
        user_from_db = User.objects.get(email=test_email)
        print(f"  SUCCESS: User found in database")
        print(f"    ID: {user_from_db.id}")
        print(f"    Username: {user_from_db.username}")
        print(f"    Email: {user_from_db.email}")
    except User.DoesNotExist:
        print(f"  ERROR: User NOT found in database!")
        return False
    
    # Step 7: Verify Staff profile
    print("\n[STEP 7] Verifying Staff profile...")
    try:
        staff = Staff.objects.get(user=user)
        print(f"  SUCCESS: Staff profile found")
        print(f"    Staff ID: {staff.staff_id}")
        print(f"    User: {staff.user.username}")
        print(f"    Maskapai: {staff.maskapai.code}")
    except Staff.DoesNotExist:
        print(f"  ERROR: Staff profile NOT found!")
        return False
    
    # Step 8: Check database state after
    print("\n[STEP 8] Checking database state AFTER registration...")
    users_after = User.objects.count()
    staff_after = Staff.objects.count()
    print(f"  Users in DB: {users_after} (added: {users_after - users_before})")
    print(f"  Staff profiles in DB: {staff_after} (added: {staff_after - staff_before})")
    
    # Step 9: Try to authenticate
    print("\n[STEP 9] Testing authentication...")
    auth_user = User.objects.get(email=test_email)
    password = 'DebugPass123!'
    is_auth = auth_user.check_password(password)
    print(f"  Password check: {is_auth}")
    if not is_auth:
        print(f"  ERROR: Password doesn't match!")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print(f"\nCreated test account:")
    print(f"  Email: {test_email}")
    print(f"  Password: {password}")
    print(f"\nYou can now try to login with this account on the website.")
    print(f"If login fails, collect the console logs and browser errors.")
    return True

if __name__ == '__main__':
    success = test_registration()
    sys.exit(0 if success else 1)
