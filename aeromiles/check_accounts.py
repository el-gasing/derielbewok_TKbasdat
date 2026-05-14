#!/usr/bin/env python
"""
Script untuk cek status registrasi dan list semua akun yang ada.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aeromiles.settings')
django.setup()

from django.contrib.auth.models import User
from auth_system.models import Staff

def show_all_accounts():
    print("=" * 80)
    print("AeroMiles - Daftar Akun yang Tersimpan di Database")
    print("=" * 80)
    
    all_users = User.objects.all().order_by('id')
    all_staff = Staff.objects.all()
    
    print(f"\nTotal Users: {all_users.count()}")
    print(f"Total Staff: {all_staff.count()}")
    print(f"Total Members: {all_users.count() - all_staff.count()}")
    
    print("\n" + "-" * 80)
    print("STAFF ACCOUNTS (dapat login):")
    print("-" * 80)
    
    if all_staff.count() == 0:
        print("  ❌ Tidak ada staff account yang tersimpan!")
    else:
        for staff in all_staff:
            print(f"\n  ID: {staff.staff_id}")
            print(f"  Email: {staff.user.email}")
            print(f"  Username: {staff.user.username}")
            print(f"  Name: {staff.user.first_name} {staff.user.last_name}")
            print(f"  Maskapai: {staff.maskapai.code if staff.maskapai else 'N/A'}")
    
    print("\n" + "-" * 80)
    print("MEMBER ACCOUNTS:")
    print("-" * 80)
    
    members = [u for u in all_users if not Staff.objects.filter(user=u).exists()]
    if len(members) == 0:
        print("  Tidak ada member account.")
    else:
        for member in members:
            print(f"\n  Email: {member.email}")
            print(f"  Username: {member.username}")
            print(f"  Name: {member.first_name} {member.last_name}")

def search_account(email_or_username):
    print("\n" + "=" * 80)
    print(f"Mencari akun: {email_or_username}")
    print("=" * 80)
    
    # Search by email
    user = User.objects.filter(email__iexact=email_or_username).first()
    if not user:
        # Search by username
        user = User.objects.filter(username__iexact=email_or_username).first()
    
    if user:
        print(f"\n✓ AKUN DITEMUKAN!")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.first_name} {user.last_name}")
        
        staff = Staff.objects.filter(user=user).first()
        if staff:
            print(f"  Type: STAFF")
            print(f"  Staff ID: {staff.staff_id}")
            print(f"  Maskapai: {staff.maskapai.code if staff.maskapai else 'N/A'}")
        else:
            print(f"  Type: MEMBER")
        
        print(f"\n  Untuk login gunakan:")
        print(f"    Email: {user.email}")
        print(f"    Username: {user.username}")
        print(f"    (Pilih salah satu)")
        
        return True
    else:
        print(f"\n✗ AKUN TIDAK DITEMUKAN dengan email/username: {email_or_username}")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Cari akun spesifik
        search_account(sys.argv[1])
    else:
        # Show all accounts
        show_all_accounts()
        
        # Prompt untuk search
        print("\n" + "=" * 80)
        email_to_search = input("\nKira-kira email mana yang you register? (atau ketik 'exit' untuk keluar): ").strip()
        if email_to_search.lower() != 'exit':
            search_account(email_to_search)
