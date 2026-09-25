from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Batch, Medicine, Placement, Sale, Shift, ShiftSchedule


@override_settings(PHARMACY_LOW_STOCK_THRESHOLD=10, PHARMACY_EXPIRY_WARNING_DAYS=30)
class DashboardTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser('owner')
        self.worker = User.objects.create_user('worker')
        group, _ = Group.objects.get_or_create(name='Aptekachi')
        self.worker.groups.add(group)
        self.url = reverse('admin:index')
        self.today = timezone.localdate()
        self.midnight = timezone.make_aware(datetime.combine(self.today, time.min))
        self.client.force_login(self.owner)

    def medicine(self, name='Test dori', stock=3):
        med = Medicine.objects.create(name=name, dosage='10 mg', form='Tabletka', package_size='10 dona', price='12.50')
        place = Placement.objects.create(medicine=med, department='A', shelf=1, row=1, quantity=stock)
        return med, place

    def sale(self, shift, place, quantity, when, cancelled=False):
        return Sale.objects.create(shift=shift, placement=place, name=place.medicine.name, dosage='10 mg', form='Tabletka', package_size='10 dona', quantity=quantity, unit_price='12.50', total=Decimal('12.50') * quantity, created_at=when, cancelled_at=when if cancelled else None)

    def test_access_navigation_and_management_destinations(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{self.url}"')
        destinations = ['admin:catalog_medicine_add', 'admin:catalog_batch_add', 'admin:auth_user_changelist', 'admin:catalog_shift_changelist', 'admin:catalog_batch_changelist', 'admin:catalog_medicine_changelist', 'admin:catalog_sale_changelist', 'admin:index']
        self.assertTemplateUsed(response, "admin/pharmacy_index.html")
        self.assertNotContains(response, "/boshqaruv/")
        for name in destinations:
            self.assertContains(response, f'href="{reverse(name)}"')
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.post(self.url).status_code, 405)
        self.client.force_login(self.worker)
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(self.url).status_code, 403)
            for name in destinations:
                self.assertEqual(method(reverse(name)).status_code, 403, name)
        self.assertNotContains(self.client.get('/'), 'Admin panel')
        self.assertNotContains(self.client.get('/'), f'href="{self.url}"')
        self.worker.is_staff = True
        self.worker.save()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), reverse('admin:login') + '?next=' + self.url)

    def test_daily_totals_boundaries_cancellations_and_top_products(self):
        med, place = self.medicine()
        second_place = Placement.objects.create(medicine=med, department='B', shelf=1, row=1, quantity=4)
        shift = Shift.objects.create(user=self.worker)
        self.sale(shift, place, 2, self.midnight)
        self.sale(shift, second_place, 3, self.midnight + timedelta(hours=23, minutes=59))
        self.sale(shift, place, 100, self.midnight + timedelta(hours=2), cancelled=True)
        self.sale(shift, place, 50, self.midnight - timedelta(microseconds=1))
        self.sale(shift, place, 60, self.midnight + timedelta(days=1))
        response = self.client.get(self.url)
        self.assertEqual(response.context['totals'], {'count': 2, 'packages': 5, 'revenue': Decimal('62.50')})
        top = list(response.context['top_medicines'])
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]['packages'], 5)
        self.assertContains(response, 'Bekor qilingan — tushumga kiritilmagan')
        self.assertEqual(len(response.context['recent_sales']), 5)

    def test_stock_and_expiration_boundaries(self):
        low, place = self.medicine(stock=4)
        Placement.objects.create(medicine=low, department='B', shelf=1, row=1, quantity=5)
        self.medicine('Yetarli', stock=10)
        zero = Medicine.objects.create(name='Joylashtirilmagan', dosage='1', form='1', price=1)
        for name, days, stock in [('expired', -1, 2), ('today', 0, 3), ('boundary', 30, 1), ('later', 31, 1), ('empty', -2, 0)]:
            batch = Batch.objects.create(medicine=low, number=name, expires_on=self.today + timedelta(days=days))
            # Separate medicine for stock aggregation assertions below.
            other, _ = self.medicine(name=name, stock=0)
            batch.medicine = other
            batch.save()
            Placement.objects.create(medicine=other, batch=batch, department=name, shelf=1, row=1, quantity=stock)
        response = self.client.get(self.url)
        stocks = {m.pk: m.stock for m in response.context['low_stock']}
        self.assertEqual(stocks[low.pk], 9)
        self.assertEqual(stocks[zero.pk], 0)
        self.assertNotIn(Medicine.objects.get(name='Yetarli').pk, stocks)
        self.assertEqual([b.number for b in response.context['expired_batches']], ['expired'])
        self.assertEqual([b.number for b in response.context['expiring_batches']], ['today', 'boundary'])
        self.assertContains(response, 'MUDDATI O‘TGAN')
        self.assertGreater(response.context['unknown_expiry_count'], 0)

    def test_shifts_include_overnight_and_unplanned_without_duplicates(self):
        plan = ShiftSchedule.objects.create(user=self.worker, planned_start=self.midnight - timedelta(hours=2), planned_end=self.midnight + timedelta(hours=6))
        actual = Shift.objects.create(user=self.worker, schedule=plan, started_at=self.midnight - timedelta(hours=1), ended_at=self.midnight + timedelta(hours=5))
        pending = ShiftSchedule.objects.create(user=self.owner, planned_start=self.midnight + timedelta(hours=8), planned_end=self.midnight + timedelta(hours=16))
        unplanned = Shift.objects.create(user=self.owner, started_at=self.midnight + timedelta(hours=1))
        ShiftSchedule.objects.create(user=self.worker, planned_start=self.midnight - timedelta(days=2), planned_end=self.midnight - timedelta(days=1))
        response = self.client.get(self.url)
        rows = response.context['shift_rows']
        self.assertEqual(len(rows), 3)
        self.assertEqual({r['shift'].pk for r in rows if r['shift']}, {actual.pk, unplanned.pk})
        self.assertEqual({r['schedule'].pk for r in rows if r['schedule']}, {plan.pk, pending.pk})
        for text in ('Yakunlangan', 'Ishlamoqda', 'Hali boshlanmagan', 'Jadvaldan tashqari'):
            self.assertContains(response, text)

    def test_empty_dashboard(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['totals'], {'count': 0, 'packages': 0, 'revenue': Decimal(0)})
        for text in ('Hali sotuvlar yo‘q.', 'Bugun uchun jadval yoki haqiqiy smena yo‘q.', 'Belgilangan chegaradan kam qolgan dorilar yo‘q.'):
            self.assertContains(response, text)

    def test_removed_dashboard_url(self):
        for user in (self.owner, self.worker):
            self.client.force_login(user)
            self.assertEqual(self.client.get('/boshqaruv/').status_code, 404)
            self.assertNotContains(self.client.get('/'), '/boshqaruv/')

    def test_inactive_owner_cannot_login(self):
        self.owner.set_password('owner-test-password')
        self.owner.is_active = False
        self.owner.save()
        self.client.logout()
        response = self.client.post(reverse('admin:login'), {
            'username': self.owner.username, 'password': 'owner-test-password',
            'next': self.url,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
