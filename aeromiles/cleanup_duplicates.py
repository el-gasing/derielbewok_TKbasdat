#!/usr/bin/env python
"""
Script untuk clean up duplicate emails dan set password yang valid.
HATI-HATI: Script ini akan DELETE user yang duplicate!
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aeromiles.settings')
django.setup()

from django.contrib.auth.models import User
from auth_system.models import Staff
from collections import defaultdict

def cleanup_duplicates():
    print("=" * 80)
    print("CLEANUP: Duplicate Email Removal")
    print("=" * 80)
    
    # Group users by email
    email_groups = defaultdict(list)
    for user in User.objects.all():
        email_groups[user.email.lower()].append(user)
    
    # Find duplicates
    duplicates = {email: users for email, users in email_groups.items() if len(users) > 1}
    
    if not duplicates:
        print("\n✓ Tidak ada duplicate email ditemukan!")
        return
    
    print(f"\nDitemukan {len(duplicates)} email dengan duplicate users:")
    
    deleted_count = 0
    for email, users in duplicates.items():
        print(f"\nEmail: {email}")
        print(f"  Total users: {len(users)}")
        
        # Sort by last_login descending (keep the most recent)
        sorted_users = sorted(users, key=lambda u: u.last_login or u.date_joined, reverse=True)
        keep_user = sorted_users[0]
        delete_users = sorted_users[1:]
        
        print(f"  KEEP: ID {keep_user.id}, Username {keep_user.username}, Last login {keep_user.last_login}")
        
        for user_to_delete in delete_users:
            staff = Staff.objects.filter(user=user_to_delete).first()
            if staff:
                print(f"    DELETE: ID {user_to_delete.id}, Username {user_to_delete.username}, Staff {staff.staff_id}")
                staff.delete()  # Delete Staff profile first (CASCADE will handle it)
            else:
                print(f"    DELETE: ID {user_to_delete.id}, Username {user_to_delete.username} (Member)")
                user_to_delete.delete()
            deleted_count += 1
    
    print("\n" + "=" * 80)
    print(f"✓ Cleanup selesai! Deleted {deleted_count} duplicate users")
    print("=" * 80)
    
    # Show remaining users
    print("\nRemaining users:")
    for user in User.objects.all().order_by('email'):
        staff = Staff.objects.filter(user=user).first()
        user_type = f"Staff ({staff.staff_id})" if staff else "Member"
        print(f"  {user.username}: {user.email} ({user_type})")

def set_known_password():
    print("\n" + "=" * 80)
    print("Set Test Password")
    print("=" * 80)
    
    # Set password untuk user yang paling baru dari ldepuuwu14
    user = User.objects.filter(email__iexact='ldepuuwu14@gmail.com').order_by('-last_login').first()
    
    if user:
        password = 'password123'  # Default test password
        user.set_password(password)
        user.save()
        print(f"\n✓ Password set untuk: {user.username} ({user.email})")
        print(f"  Password: {password}")
        print(f"  Anda sekarang bisa login dengan:")
        print(f"    Email: {user.email}")
        print(f"    Username: {user.username}")
        print(f"    Password: {password}")
    else:
        print(f"\n✗ User dengan email ldepuuwu14@gmail.com tidak ditemukan")

if __name__ == '__main__':
    confirm = input("\n⚠️  Script ini akan DELETE user dengan duplicate email!\nLanjutkan? (yes/no): ").strip().lower()
    if confirm == 'yes':
        cleanup_duplicates()
        set_known_password()
    else:
        print("Cancelled.")
