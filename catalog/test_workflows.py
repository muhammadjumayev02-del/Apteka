from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import Group, User
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from .models import Medicine, Placement, Batch, Sale, Shift, StockTransfer


class WorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        group = Group.objects.create(name='Aptekachi')
        cls.worker = User.objects.create_user('worker')
        cls.other = User.objects.create_user('other')
        cls.outsider = User.objects.create_user('outsider', is_staff=True)
        for user in (cls.worker, cls.other):
            user.groups.add(group)
        cls.admin = User.objects.create_superuser('admin', password='test-pass')
        cls.med = Medicine.objects.create(name='Namuna Alfa', dosage='10 mg', form='Tabletka',
                                         package_size='20 tabletka', alternative_names='Альфа sinonim', price='1250.50')
        cls.place = Placement.objects.create(medicine=cls.med, department='A', shelf=1, row=1, quantity=10)
        cls.place.batch.expires_on = timezone.localdate() + timedelta(days=365)
        cls.place.batch.save()
        cls.batch2 = Batch.objects.create(medicine=cls.med, number='B-2')
        cls.place2 = Placement.objects.create(medicine=cls.med, batch=cls.batch2, department='A', shelf=1, row=1, quantity=5)
        cls.empty = Placement.objects.create(medicine=cls.med, department='Bo‘sh joy', shelf=9, row=9, quantity=0)

    def setUp(self):
        self.client.force_login(self.worker)

    def start(self):
        self.client.post(reverse('catalog:shifts'), {'action': 'start'})
        return Shift.objects.get(user=self.worker, ended_at__isnull=True)

    def preview(self, quantity=2):
        return self.client.post(reverse('catalog:sell', args=[self.med.pk]), {'placement': self.place.pk, 'quantity': quantity})

    def confirm(self, token):
        return self.client.post(reverse('catalog:sale_confirm'), {'token': token})

    def test_search_scripts_alias_typo_and_explicit_selection(self):
        for q in ('Намуна Алфа', 'namuna alfa', 'альфа', 'sinonim', 'alffa'):
            response = self.client.get('/', {'q': q})
            self.assertContains(response, 'Namuna Alfa')
            self.assertContains(response, '10 mg')
            self.assertContains(response, 'Tabletka')
            self.assertContains(response, '20 tabletka')
            self.assertNotIn('Location', response)
        self.assertContains(self.client.get('/', {'q': 'alffa'}), 'Ehtimoliy natijalar')
        Medicine.objects.create(name='Namuna Alfa', dosage='20 mg', form='Kapsula', package_size='30 kapsula', price=2)
        response = self.client.get('/', {'q': 'alfa'})
        self.assertEqual(len(response.context['page_obj']), 2)
        self.assertContains(response, '30 kapsula')

    def test_preview_does_not_mutate_confirmation_is_once(self):
        shift = self.start()
        response = self.preview()
        self.assertTemplateUsed(response, 'catalog/confirm_sale.html')
        for text in ('Sotuvni tasdiqlash', '20 tabletka', '2501,00'):
            self.assertContains(response, text)
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 10)
        self.assertFalse(Sale.objects.exists())
        token = response.context['token']
        self.confirm(token)
        self.confirm(token)
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 8)
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(Sale.objects.get().total, Decimal('2501'))
        self.assertEqual(Sale.objects.get().shift, shift)

    def test_invalid_and_other_users_confirmation_rejected(self):
        self.start()
        token = self.preview().context['token']
        self.confirm(token + 'bad')
        self.client.force_login(self.other)
        self.assertEqual(self.confirm(token).status_code, 403)
        self.assertFalse(Sale.objects.exists())

    def test_recheck_stock_price_product_and_shift(self):
        self.start()
        token = self.preview().context['token']
        Placement.objects.filter(pk=self.place.pk).update(quantity=1)
        self.confirm(token)
        self.assertFalse(Sale.objects.exists())
        Placement.objects.filter(pk=self.place.pk).update(quantity=10)
        self.med.price = Decimal('5000')
        self.med.save()
        self.confirm(token)
        self.assertFalse(Sale.objects.exists())
        token = self.preview().context['token']
        self.med.dosage = '50 mg'
        self.med.save()
        self.confirm(token)
        self.assertFalse(Sale.objects.exists())
        token = self.preview().context['token']
        self.client.post(reverse('catalog:shifts'), {'action': 'end'})
        self.confirm(token)
        self.assertFalse(Sale.objects.exists())
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 10)

    def test_sale_requires_shift_package_and_positive_valid_stock(self):
        self.assertContains(self.preview(), 'Avval smenani boshlang')
        self.start()
        for quantity in (0, -1, 11):
            self.assertTemplateUsed(self.preview(quantity), 'catalog/sell.html')
        self.med.package_size = ''
        self.med.save()
        self.assertContains(self.preview(), 'qadoq hajmini kiritishi kerak')
        self.assertFalse(Sale.objects.exists())

    def test_shift_isolation_cancel_totals_and_unique_open_shift(self):
        shift = self.start()
        self.start()
        self.assertEqual(Shift.objects.filter(user=self.worker).count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Shift.objects.create(user=self.worker)
        self.confirm(self.preview(3).context['token'])
        sale = Sale.objects.get()
        response = self.client.get(reverse('catalog:shift_detail', args=[shift.pk]))
        self.assertEqual(response.context['totals'], {'quantity': 3, 'total': Decimal('3751.5')})
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('catalog:shift_detail', args=[shift.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('catalog:sale_cancel', args=[sale.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('catalog:shifts')), 'worker')
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('catalog:shifts')), 'worker')
        self.assertEqual(self.client.get(reverse('catalog:shift_detail', args=[shift.pk])).status_code, 200)
        for _ in range(2):
            self.client.post(reverse('catalog:sale_cancel', args=[sale.pk]))
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 10)
        response = self.client.get(reverse('catalog:shift_detail', args=[shift.pk]))
        self.assertEqual(response.context['totals'], {'quantity': 0, 'total': Decimal(0)})
        self.assertEqual(Sale.objects.count(), 1)

    def test_locations_omit_zero_and_show_each_batch(self):
        response = self.client.get(reverse('catalog:locations', args=[self.med.pk]))
        self.assertContains(response, '10 pachka')
        self.assertContains(response, '5 pachka')
        self.assertNotContains(response, 'Bo‘sh joy')
        self.assertContains(response, 'B-2')
        self.assertContains(self.client.get('/'), 'Qayerda turibdi?')
        self.assertContains(self.client.get(self.med.get_absolute_url()), 'Qayerda turibdi?')

    def transfer(self, quantity=4, **kwargs):
        return self.client.post(reverse('catalog:transfer', args=[self.med.pk]),
                                dict(source=self.place.pk, department='B', shelf=2, row=3, quantity=quantity, **kwargs))

    def test_transfer_conserves_stock_and_batch_with_audit(self):
        self.client.force_login(self.admin)
        for count in (4, 2):
            self.assertEqual(self.transfer(count).status_code, 302)
        self.place.refresh_from_db()
        self.place2.refresh_from_db()
        self.assertEqual(self.place.quantity, 4)
        self.assertEqual(self.place2.quantity, 5)
        dest = Placement.objects.get(medicine=self.med, department='B')
        self.assertEqual(dest.quantity, 6)
        self.assertEqual(dest.batch_id, self.place.batch_id)
        self.assertEqual(self.med.placements.aggregate(n=Sum('quantity'))['n'], 15)
        self.assertEqual(StockTransfer.objects.count(), 2)
        audit = StockTransfer.objects.first()
        self.assertEqual(audit.user, self.admin)
        self.assertEqual(audit.source_label, str(self.place))
        self.assertEqual(audit.destination_label, str(dest))
        self.assertIsNotNone(audit.created_at)

    def test_transfer_rejects_excess_same_place_and_foreign_medicine(self):
        self.client.force_login(self.admin)
        self.assertContains(self.transfer(11), 'qoldiq yetarli emas')
        self.assertEqual(self.transfer(0).status_code, 200)
        response = self.client.post(reverse('catalog:transfer', args=[self.med.pk]),
                                   {'source': self.place.pk, 'department': 'A', 'shelf': 1, 'row': 1, 'quantity': 1})
        self.assertContains(response, 'bir xil')
        other = Medicine.objects.create(name='Other', dosage='1', form='1', price=1)
        foreign = Placement.objects.create(medicine=other, department='X', shelf=1, row=1, quantity=9)
        self.client.post(reverse('catalog:transfer', args=[self.med.pk]),
                         {'source': foreign.pk, 'department': 'B', 'shelf': 2, 'row': 3, 'quantity': 1})
        self.assertFalse(StockTransfer.objects.exists())
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 10)

    def test_new_routes_permissions_methods_csrf(self):
        routes = [reverse('catalog:locations', args=[self.med.pk]), reverse('catalog:sell', args=[self.med.pk]),
                  reverse('catalog:shifts'), reverse('catalog:shift_detail', args=[1]),
                  reverse('catalog:sale_cancel', args=[1]), reverse('catalog:sale_confirm'),
                  reverse('catalog:transfer', args=[self.med.pk])]
        for user, status in ((self.outsider, 403), (None, 302)):
            if user:
                self.client.force_login(user)
            else:
                self.client.logout()
            for url in routes:
                self.assertEqual(self.client.get(url).status_code, status)
                self.assertEqual(self.client.post(url).status_code, status)
        self.client.force_login(self.worker)
        self.assertEqual(self.transfer().status_code, 403)
        self.assertEqual(self.client.get(reverse('catalog:transfer', args=[self.med.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('catalog:sale_confirm')).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        for url in routes:
            self.assertEqual(client.post(url).status_code, 403)

    def test_confirmation_expiry_and_changed_location(self):
        from unittest.mock import patch
        self.start()
        token = self.preview().context['token']
        with patch('django.core.signing.time.time', return_value=9999999999):
            self.confirm(token)
        self.assertFalse(Sale.objects.exists())
        Placement.objects.filter(pk=self.place.pk).update(shelf=8)
        self.confirm(token)
        self.assertFalse(Sale.objects.exists())

    def test_transfer_rolls_back_if_audit_cannot_be_saved(self):
        from unittest.mock import patch
        self.client.force_login(self.admin)
        with patch('catalog.services.StockTransfer.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.transfer()
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 10)
        self.assertFalse(Placement.objects.filter(department='B').exists())

    def test_history_cannot_be_deleted_or_edited_in_admin(self):
        self.start()
        self.confirm(self.preview().context['token'])
        sale = Sale.objects.get()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse('admin:catalog_sale_delete', args=[sale.pk]), {'post': 'yes'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin:catalog_sale_change', args=[sale.pk]), {'total': '0'}).status_code, 403)
        self.client.post(reverse('admin:catalog_medicine_delete', args=[self.med.pk]), {'post': 'yes'})
        self.assertTrue(Medicine.objects.filter(pk=self.med.pk).exists())
        self.assertTrue(Sale.objects.filter(pk=sale.pk).exists())


class PreservationMigrationTests(TransactionTestCase):
    def test_existing_stock_and_medicine_survive_migration(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        executor.migrate([('catalog', '0001_initial')])
        try:
            apps = executor.loader.project_state([('catalog', '0001_initial')]).apps
            med = apps.get_model('catalog', 'Medicine').objects.create(name='Old', dosage='1', form='Tablet', price=4, search_text='old')
            place = apps.get_model('catalog', 'Placement').objects.create(medicine_id=med.pk, department='Old shelf', shelf=3, row=2, quantity=17)
            medicine_id, place_id = med.pk, place.pk
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
        self.assertEqual(Medicine.objects.get(pk=medicine_id).name, 'Old')
        preserved = Placement.objects.get(pk=place_id)
        self.assertEqual(preserved.quantity, 17)
        self.assertEqual(preserved.department, 'Old shelf')
        self.assertEqual(preserved.batch.number, 'Boshlang‘ich partiya')
