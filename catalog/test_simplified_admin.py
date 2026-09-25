from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from .models import Medicine, Placement, Shift, Sale
from .forms import SaleForm, TransferForm


class SimplifiedAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser('owner')
        cls.worker = User.objects.create_user('worker')
        cls.worker.groups.add(Group.objects.create(name='Aptekachi'))
        cls.other = User.objects.create_user('other')
        cls.other.groups.add(Group.objects.get(name='Aptekachi'))
        cls.medicine = Medicine.objects.create(name='Sinov', dosage='10 mg', form='Tabletka', package_size='20 dona', price=100)
        cls.place = Placement.objects.create(medicine=cls.medicine, department='A', shelf=1, row=1, quantity=5)
        cls.shift = Shift.objects.create(user=cls.worker)
        cls.sale = Sale.objects.create(shift=cls.shift, placement=cls.place, name='Sinov', dosage='10 mg', form='Tabletka', package_size='20 dona', quantity=2, unit_price=100, total=200)

    def test_cancel_preview_is_read_only_and_private(self):
        url = reverse('catalog:sale_cancel', args=[self.sale.pk])
        self.client.force_login(self.worker)
        self.assertContains(self.client.get(url), 'Ha, sotuvni bekor qilish')
        self.sale.refresh_from_db()
        self.place.refresh_from_db()
        self.assertIsNone(self.sale.cancelled_at)
        self.assertEqual(self.place.quantity, 5)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.worker)
        self.assertContains(self.client.post(url, follow=True), 'Pachkalar qoldiqqa qaytarildi.')
        self.client.post(url)
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 7)

    def test_stock_errors_are_attached_to_quantity(self):
        for form in [SaleForm({'placement': self.place.pk, 'quantity': 6}, medicine=self.medicine), TransferForm({'source': self.place.pk, 'quantity': 6, 'department': 'B', 'shelf': 2, 'row': 1}, medicine=self.medicine)]:
            self.assertFalse(form.is_valid())
            self.assertIn('quantity', form.errors)
            self.assertIn('5 pachka', str(form.errors['quantity']))

    def test_owner_shortcuts_and_worker_visibility(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('admin:index'))
        for label in ['Dori qidirish', 'Sotuv qilish', 'Dori qo‘shish', 'Qoldiqni ko‘rish', 'Hisobotlar']:
            self.assertContains(response, label)
        self.client.force_login(self.worker)
        response = self.client.get(reverse('catalog:home'))
        self.assertContains(response, reverse('catalog:sell', args=[self.medicine.pk]))
        self.assertNotContains(response, reverse('catalog:create'))
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 403)
