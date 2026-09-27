from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from .models import Batch, Medicine, Placement, Sale, Shift
from .services import cancel_sale, confirm_sale, snapshot
from . import test_workflows


class ExpiryTests(TestCase):
    setUpTestData = classmethod(test_workflows.WorkflowTests.setUpTestData.__func__)
    setUp = test_workflows.WorkflowTests.setUp
    start = test_workflows.WorkflowTests.start
    preview = test_workflows.WorkflowTests.preview
    confirm = test_workflows.WorkflowTests.confirm
    def test_expired_and_missing_date_block_preview_in_both_languages(self):
        self.start()
        for language, message in [('uz', 'Sotish mumkin emas'), ('ru', 'Продажа запрещена')]:
            self.client.cookies['django_language'] = language
            Batch.objects.filter(pk=self.place.batch_id).update(expires_on=timezone.localdate()-timedelta(days=1))
            self.assertContains(self.preview(), message)
        Batch.objects.filter(pk=self.place.batch_id).update(expires_on=None)
        self.assertTemplateUsed(self.preview(), 'catalog/sell.html')
        self.assertFalse(Sale.objects.exists())

    def test_expiry_rechecked_after_preview_and_today_allowed(self):
        self.start()
        Batch.objects.filter(pk=self.place.batch_id).update(expires_on=timezone.localdate())
        token = self.preview().context['token']
        Batch.objects.filter(pk=self.place.batch_id).update(expires_on=timezone.localdate()-timedelta(days=1))
        self.confirm(token)
        self.assertFalse(Sale.objects.exists())
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 10)
        Batch.objects.filter(pk=self.place.batch_id).update(expires_on=timezone.localdate())
        self.confirm(token)
        self.assertEqual(Sale.objects.count(), 1)

    def test_sale_audit_failure_rolls_back_stock(self):
        self.start()
        token = self.preview().context['token']
        with patch('catalog.services.Sale.objects.create', side_effect=RuntimeError('audit')):
            with self.assertRaises(RuntimeError):
                self.confirm(token)
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 10)

    def test_repeat_cancel_reports_error_and_keeps_other_batch(self):
        self.start()
        self.confirm(self.preview().context['token'])
        sale = Sale.objects.get()
        url = reverse('catalog:sale_cancel', args=[sale.pk])
        self.client.post(url)
        self.assertContains(self.client.post(url, follow=True), 'allaqachon bekor qilingan')
        self.place.refresh_from_db()
        self.place2.refresh_from_db()
        self.assertEqual((self.place.quantity, self.place2.quantity), (10, 5))


class ConcurrentSalesTests(TransactionTestCase):
    def setUp(self):
        # SQLite shared in-memory databases have different locking behaviour.
        # Use a real temporary database file for independent connections.
        self.original_name = connections['default'].settings_dict['NAME']
        self.tmp = TemporaryDirectory()
        if connections['default'].vendor == 'sqlite':
            connection = connections['default']
            connection.ensure_connection()
            import sqlite3
            path = str(Path(self.tmp.name) / 'concurrency.sqlite3')
            with sqlite3.connect(path) as destination:
                connection.connection.backup(destination)
            self.original_connection = connection.connection
            connection.connection = None
            connection.settings_dict['NAME'] = path
        self.users = [User.objects.create_user('parallel'+str(i)) for i in range(2)]
        self.med = Medicine.objects.create(name='Concurrency', dosage='1', form='Tablet', package_size='10', price=Decimal('12.35'))
        self.batch = Batch.objects.create(medicine=self.med, number='C', expires_on=timezone.localdate()+timedelta(days=1))
        self.place = Placement.objects.create(medicine=self.med, batch=self.batch, department='A', shelf=1, row=1, quantity=3)
        self.data = [dict(medicine=self.med.pk, placement=self.place.pk, batch=self.batch.pk,
                          location=self.place.location_key, product=snapshot(self.med), price=str(self.med.price),
                          quantity=2, payment_method='cash', shift=Shift.objects.create(user=user).pk, token=str(uuid.uuid4())) for user in self.users]

    def tearDown(self):
        if connections['default'].vendor == 'sqlite':
            connections['default'].close()
            connections['default'].settings_dict['NAME'] = self.original_name
            connections['default'].connection = self.original_connection
        self.tmp.cleanup()

    def parallel(self, action):
        barrier = Barrier(2)
        db_name = connections['default'].settings_dict['NAME']
        def run(index):
            conn = connections['default']
            conn.settings_dict['NAME'] = db_name
            try:
                barrier.wait(timeout=10)
                return action(index)
            finally:
                conn.close()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(run, range(2)))

    def test_two_workers_cannot_oversell_same_batch(self):
        def sell(index):
            try:
                confirm_sale(self.users[index], self.data[index])
                return 'sold'
            except ValidationError:
                return 'rejected'
        self.assertCountEqual(self.parallel(sell), ['sold', 'rejected'])
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 1)
        self.assertEqual(Sale.objects.get().total, Decimal('24.70'))

    def test_simultaneous_cancellation_returns_stock_once(self):
        sale = confirm_sale(self.users[0], self.data[0])
        self.assertCountEqual(self.parallel(lambda index: cancel_sale(sale, self.users[0])), [True, False])
        self.place.refresh_from_db()
        self.assertEqual(self.place.quantity, 3)
