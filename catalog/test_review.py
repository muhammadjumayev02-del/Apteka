"""Regression coverage for the readiness review, using isolated test data."""
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from . import test_workflows
from .forms import PlacementForm
from .models import Placement, Sale, StockTransfer


class ReviewTests(TestCase):
    setUpTestData = classmethod(test_workflows.WorkflowTests.setUpTestData.__func__)
    setUp = test_workflows.WorkflowTests.setUp
    start = test_workflows.WorkflowTests.start
    preview = test_workflows.WorkflowTests.preview
    confirm = test_workflows.WorkflowTests.confirm

    def edit_payload(self, admin=False):
        self.client.force_login(self.admin)
        url = reverse('admin:catalog_medicine_change' if admin else 'catalog:edit', args=[self.med.pk])
        response = self.client.get(url)
        formset = (response.context['inline_admin_formsets'][0].formset if admin
                   else response.context['placements'])
        prefix = formset.prefix
        payload = dict(name=self.med.name, dosage=self.med.dosage, form=self.med.form,
                       price=str(self.med.price), package_size=self.med.package_size,
                       alternative_names=self.med.alternative_names)
        payload.update({f'{prefix}-TOTAL_FORMS': str(formset.initial_form_count()),
                        f'{prefix}-INITIAL_FORMS': str(formset.initial_form_count())})
        for form in formset.initial_forms:
            for key, value in form.initial.items():
                payload[f'{form.prefix}-{key}'] = '' if value is None else str(value)
            payload[f'{form.prefix}-id'] = str(form.instance.pk)
        return url, payload

    def test_empty_sale_post_without_shift_is_validation_error(self):
        response = self.client.post(reverse('catalog:sell', args=[self.med.pk]), {})
        self.assertContains(response, 'Sotuv uchun smenani admin ochishi kerak.')
        self.assertFalse(Sale.objects.exists())

    def test_stale_admin_and_catalog_forms_cannot_restore_sold_stock(self):
        self.start()
        for admin in (False, True):
            url, payload = self.edit_payload(admin)
            self.client.force_login(self.worker)
            self.confirm(self.preview(2).context['token'])
            quantity = Placement.objects.get(pk=self.place.pk).quantity
            self.client.force_login(self.admin)
            response = self.client.post(url, payload)
            self.assertContains(response, 'Qoldiq yoki joylashuv o‘zgargan')
            self.assertEqual(Placement.objects.get(pk=self.place.pk).quantity, quantity)
            # Refreshing the form permits a deliberate stock correction.
            url, payload = self.edit_payload(admin)
            saved = self.client.post(url, payload)
            errors = ([(inline.formset.errors, inline.formset.non_form_errors()) for inline in saved.context['inline_admin_formsets']] if admin and saved.status_code == 200 else (saved.context['form'].errors, saved.context['placements'].errors) if saved.status_code == 200 else '')
            self.assertEqual(saved.status_code, 302, errors)

    def test_missing_or_tampered_snapshot_cannot_change_existing_stock(self):
        for value in ('', 'forged'):
            form = PlacementForm(dict(batch=self.place.batch_id, department='A', shelf=1,
                                      row=1, quantity=99, stock_snapshot=value), instance=self.place)
            self.assertFalse(form.is_valid())
        self.assertEqual(Placement.objects.get(pk=self.place.pk).quantity, 10)

    def test_russian_missing_package_and_historical_locations(self):
        self.med.package_size = ''
        self.med.save()
        self.client.cookies['django_language'] = 'ru'
        for url in ('/', self.med.get_absolute_url()):
            response = self.client.get(url)
            self.assertNotContains(response, 'Qadoq hajmi kiritilmagan')
        transfer = StockTransfer.objects.create(source=self.place, destination=self.place2,
            source_label=self.place.location_key, destination_label=self.place2.location_key,
            quantity=1, user=self.admin)
        with override('ru'):
            self.assertIn('полка', transfer.source_display)
            self.assertNotIn('polka', transfer.destination_display)
        self.client.force_login(self.admin)
        for url in (reverse('catalog:transfer', args=[self.med.pk]),
                    reverse('admin:catalog_stocktransfer_change', args=[transfer.pk])):
            self.assertNotContains(self.client.get(url), '-polka')
        transfer.refresh_from_db()
        self.assertEqual(transfer.source_label, self.place.location_key)
