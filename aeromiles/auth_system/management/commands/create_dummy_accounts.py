from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection


class Command(BaseCommand):
    help = 'Buat akun dummy staff dan member untuk testing deployment'

    def handle(self, *args, **options):
        self._create_superuser()
        self._create_member()
        self._create_staff()

    def _create_superuser(self):
        email = 'admin@aeromiles.test'
        username = 'admin'
        password = 'Admin123!'

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" sudah ada, skip.'))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(
            f'\n[ADMIN/SUPERUSER]\n  username : {username}\n  email    : {email}\n  password : {password}\n  django admin: /admin/'
        ))

    def _create_member(self):
        email = 'member@aeromiles.test'
        username = 'member_test'
        password = 'Member123!'

        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(self.style.WARNING(f'Member "{email}" sudah ada, skip.'))
            return

        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name='Member', last_name='Test',
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM auth_system_tier ORDER BY minimal_tier_miles ASC LIMIT 1"
            )
            row = cursor.fetchone()
            tier_id = row[0] if row else None

            cursor.execute("""
                INSERT INTO auth_system_member
                    (user_id, member_id, salutation, country_code, phone_number,
                     birth_date, nationality, tier_id, total_miles, award_miles,
                     is_active, created_at, updated_at)
                VALUES (%s, %s, 'Mr', '+62', '08123456789',
                        '1990-01-01', 'Indonesian', %s, 5000, 5000,
                        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, [user.id, 'MBR-DUMMY-001', tier_id])

        self.stdout.write(self.style.SUCCESS(
            f'\n[MEMBER]\n  username : {username}\n  email    : {email}\n  password : {password}'
        ))

    def _create_staff(self):
        email = 'staff@aeromiles.test'
        username = 'staff_test'
        password = 'Staff123!'

        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(self.style.WARNING(f'Staff "{email}" sudah ada, skip.'))
            return

        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM auth_system_maskapai LIMIT 1")
            row = cursor.fetchone()
            if not row:
                self.stdout.write(self.style.ERROR('Tidak ada maskapai di DB. Jalankan SQL dump TK3 dulu.'))
                return
            maskapai_id = row[0]

        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name='Staff', last_name='Test', is_staff=True,
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT staff_id FROM auth_system_staff ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row and row[0].startswith('STF'):
                try:
                    last_num = int(row[0][3:])
                except ValueError:
                    last_num = 0
            else:
                last_num = 0
            staff_id = f'STF{last_num + 1:03d}'

            cursor.execute("""
                INSERT INTO auth_system_staff
                    (user_id, staff_id, salutation, country_code, phone_number,
                     birth_date, nationality, maskapai_id, department,
                     is_active, created_at, updated_at)
                VALUES (%s, %s, 'Mr', '+62', '08987654321',
                        '1985-06-15', 'Indonesian', %s, 'Operations',
                        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, [user.id, staff_id, maskapai_id])

        self.stdout.write(self.style.SUCCESS(
            f'\n[STAFF]\n  username : {username}\n  email    : {email}\n  password : {password}'
        ))
