from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import ClaimMissingMiles, Member, Staff, TransferMiles


class AuthAndMilesWorkflowTests(TestCase):
	def setUp(self):
		self.member_user = User.objects.create_user(
			username='member1',
			password='memberpass123',
			first_name='Member',
		)
		self.member = Member.objects.create(
			user=self.member_user,
			member_id='AMS000001',
			total_miles=1000,
			is_active=True,
		)

		self.member2_user = User.objects.create_user(
			username='member2',
			password='memberpass123',
			first_name='Member2',
		)
		self.member2 = Member.objects.create(
			user=self.member2_user,
			member_id='AMS000002',
			total_miles=200,
			is_active=True,
		)

		self.staff_user = User.objects.create_user(
			username='staff1',
			password='staffpass123',
			first_name='Staff',
		)
		self.staff = Staff.objects.create(
			user=self.staff_user,
			staff_id='STF000001',
			department='customer_service',
			is_active=True,
		)

	def test_login_and_logout_flow(self):
		login_url = reverse('auth_system:login')
		dashboard_url = reverse('auth_system:dashboard')

		response = self.client.post(
			login_url,
			data={'username': 'member1', 'password': 'memberpass123'},
			follow=True,
		)

		self.assertRedirects(response, dashboard_url)
		self.assertTrue(response.context['user'].is_authenticated)

		logout_response = self.client.get(reverse('auth_system:logout'), follow=True)
		self.assertRedirects(logout_response, login_url)
		self.assertFalse(logout_response.context['user'].is_authenticated)

	def test_member_claim_crud(self):
		self.client.login(username='member1', password='memberpass123')

		create_response = self.client.post(
			reverse('auth_system:member_claim_create'),
			data={
				'flight_number': 'GA123',
				'flight_date': date.today(),
				'miles_amount': 300,
				'reason': 'Miles belum masuk',
				'description': 'Boarding pass sudah tersedia',
			},
			follow=True,
		)

		self.assertEqual(create_response.status_code, 200)
		claim = ClaimMissingMiles.objects.get(member=self.member)
		self.assertEqual(claim.status, 'pending')

		update_response = self.client.post(
			reverse('auth_system:member_claim_update', args=[claim.id]),
			data={
				'flight_number': 'GA123',
				'flight_date': claim.flight_date,
				'miles_amount': 350,
				'reason': 'Miles belum masuk',
				'description': 'Updated description',
			},
			follow=True,
		)
		self.assertEqual(update_response.status_code, 200)

		claim.refresh_from_db()
		self.assertEqual(claim.miles_amount, 350)

		delete_response = self.client.post(
			reverse('auth_system:member_claim_delete', args=[claim.id]),
			follow=True,
		)
		self.assertEqual(delete_response.status_code, 200)
		self.assertFalse(ClaimMissingMiles.objects.filter(id=claim.id).exists())

	def test_staff_can_read_and_update_claim(self):
		claim = ClaimMissingMiles.objects.create(
			member=self.member,
			claim_id='CLM000010',
			flight_number='GA456',
			flight_date=date.today(),
			miles_amount=500,
			reason='Flight completed but miles missing',
			status='pending',
		)

		self.client.login(username='staff1', password='staffpass123')

		list_response = self.client.get(reverse('auth_system:staff_claim_list'))
		self.assertEqual(list_response.status_code, 200)
		self.assertContains(list_response, claim.claim_id)

		update_response = self.client.post(
			reverse('auth_system:staff_claim_update', args=[claim.id]),
			data={
				'status': 'approved',
				'description': 'Diverifikasi dan disetujui',
			},
			follow=True,
		)
		self.assertEqual(update_response.status_code, 200)

		claim.refresh_from_db()
		self.assertEqual(claim.status, 'approved')
		self.assertEqual(claim.approved_by, self.staff)

	def test_member_transfer_create_and_read(self):
		self.client.login(username='member1', password='memberpass123')

		response = self.client.post(
			reverse('auth_system:member_transfer_create'),
			data={
				'to_member_id': self.member2.member_id,
				'miles_amount': 250,
				'description': 'Gift miles',
			},
			follow=True,
		)
		self.assertEqual(response.status_code, 200)

		transfer = TransferMiles.objects.get(from_member=self.member, to_member=self.member2)
		self.assertEqual(transfer.status, 'completed')

		self.member.refresh_from_db()
		self.member2.refresh_from_db()
		self.assertEqual(self.member.total_miles, 750)
		self.assertEqual(self.member2.total_miles, 450)
