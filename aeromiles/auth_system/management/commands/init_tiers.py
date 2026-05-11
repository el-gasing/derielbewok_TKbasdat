"""
Management command to initialize Tier data for AeroMiles application.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from auth_system.models import Tier


class Command(BaseCommand):
    help = 'Initialize Tier data with default tier levels (Bronze, Silver, Gold, Platinum)'

    def handle(self, *args, **options):
        tiers_data = [
            {
                'tier_name': 'bronze',
                'minimal_tier_miles': 0,
                'minimal_frekuensi_terbang': 1,
                'is_active': True,
                'description': 'Entry level tier for new members'
            },
            {
                'tier_name': 'silver',
                'minimal_tier_miles': 10000,
                'minimal_frekuensi_terbang': 5,
                'is_active': True,
                'description': 'Frequent flyer tier'
            },
            {
                'tier_name': 'gold',
                'minimal_tier_miles': 25000,
                'minimal_frekuensi_terbang': 10,
                'is_active': True,
                'description': 'Very frequent flyer tier'
            },
            {
                'tier_name': 'platinum',
                'minimal_tier_miles': 50000,
                'minimal_frekuensi_terbang': 20,
                'is_active': True,
                'description': 'Elite member tier'
            },
        ]

        created_count = 0
        skipped_count = 0

        for tier_data in tiers_data:
            tier, created = Tier.objects.get_or_create(
                tier_name=tier_data['tier_name'],
                defaults={
                    'minimal_tier_miles': tier_data['minimal_tier_miles'],
                    'minimal_frekuensi_terbang': tier_data['minimal_frekuensi_terbang'],
                    'is_active': tier_data['is_active'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created tier: {tier.get_tier_name_display()} '
                        f'(min {tier_data["minimal_tier_miles"]} miles, '
                        f'min {tier_data["minimal_frekuensi_terbang"]} flights)'
                    )
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'⊘ Tier already exists: {tier.get_tier_name_display()}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Tier initialization complete! '
                f'Created: {created_count}, Skipped: {skipped_count}'
            )
        )
