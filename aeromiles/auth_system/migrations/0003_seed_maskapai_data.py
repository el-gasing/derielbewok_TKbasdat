from django.db import migrations


def seed_maskapai(apps, schema_editor):
    Maskapai = apps.get_model('auth_system', 'Maskapai')

    initial_maskapai = [
        {'name': 'Garuda Indonesia', 'code': 'GA', 'email': 'contact@garuda-indonesia.test'},
        {'name': 'Singapore Airlines', 'code': 'SQ', 'email': 'contact@singapore-airlines.test'},
        {'name': 'Malaysia Airlines', 'code': 'MH', 'email': 'contact@malaysia-airlines.test'},
        {'name': 'AirAsia', 'code': 'AK', 'email': 'contact@airasia.test'},
        {'name': 'Lion Air', 'code': 'JT', 'email': 'contact@lionair.test'},
        {'name': 'Batik Air', 'code': 'ID', 'email': 'contact@batikair.test'},
        {'name': 'Citilink', 'code': 'QG', 'email': 'contact@citilink.test'},
        {'name': 'Emirates', 'code': 'EK', 'email': 'contact@emirates.test'},
        {'name': 'Qatar Airways', 'code': 'QR', 'email': 'contact@qatarairways.test'},
        {'name': 'Cathay Pacific', 'code': 'CX', 'email': 'contact@cathaypacific.test'},
    ]

    for item in initial_maskapai:
        Maskapai.objects.update_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'email': item['email'],
                'is_active': True,
            },
        )


def unseed_maskapai(apps, schema_editor):
    Maskapai = apps.get_model('auth_system', 'Maskapai')
    seed_codes = ['GA', 'SQ', 'MH', 'AK', 'JT', 'ID', 'QG', 'EK', 'QR', 'CX']
    Maskapai.objects.filter(code__in=seed_codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth_system', '0002_member_birth_date_member_country_code_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_maskapai, unseed_maskapai),
    ]
