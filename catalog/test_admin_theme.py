from html.parser import HTMLParser

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

from .models import Medicine, Placement, Shift, Sale, StockTransfer


class NavigationParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.in_navigation = False
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'nav':
            self.in_navigation = attrs.get('aria-label') == 'Boshqaruv amallari'
        elif tag == 'a' and self.in_navigation:
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'nav':
            self.in_navigation = False


class AdminThemeTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser('theme-owner', password='Theme-Test-921!')
        self.worker = User.objects.create_user('theme-worker', is_staff=True)
        self.medicine = Medicine.objects.create(name='Theme medicine', dosage='10 mg', form='Tabletka', price=100)
        self.place = Placement.objects.create(medicine=self.medicine, department='A', shelf=1, row=1, quantity=10)
        self.shift = Shift.objects.create(user=self.worker)
        self.sale = Sale.objects.create(shift=self.shift, placement=self.place, name='Theme medicine', dosage='10 mg', form='Tabletka', package_size='', quantity=1, unit_price=100, total=100)
        self.transfer = StockTransfer.objects.create(source=self.place, destination=self.place, source_label='A', destination_label='B', quantity=1, user=self.worker)
        self.client.force_login(self.owner)

    def page_urls(self):
        yield reverse('admin:index')
        for model, obj in [('catalog_medicine', self.medicine), ('catalog_batch', self.place.batch), ('auth_user', self.worker), ('catalog_shift', self.shift), ('catalog_sale', self.sale), ('catalog_stocktransfer', self.transfer)]:
            yield reverse(f'admin:{model}_changelist')
            yield reverse(f'admin:{model}_change', args=[obj.pk])
            yield reverse(f'admin:{model}_history', args=[obj.pk])
            if model in ('catalog_medicine', 'catalog_batch', 'auth_user'):
                yield reverse(f'admin:{model}_add')
                yield reverse(f'admin:{model}_delete', args=[obj.pk])
        yield reverse('admin:auth_group_changelist')
        yield reverse('admin:auth_group_add')
        yield reverse('admin:password_change')
        yield reverse('admin:app_list', args=['catalog'])
        yield reverse('admin:auth_user_password_change', args=[self.worker.pk])

    def assert_navigation(self, response, expected_url=None):
        links = NavigationParser(response.content.decode()).links
        self.assertEqual([link['href'] for link in links], [
            reverse(f'admin:{name}') for name in (
                'catalog_medicine_changelist', 'catalog_medicine_add',
                'catalog_batch_changelist', 'catalog_batch_add',
                'auth_user_changelist', 'catalog_shift_changelist',
                'catalog_sale_changelist', 'catalog_stocktransfer_changelist',
            )
        ])
        for link in links:
            active = link['href'] == expected_url
            self.assertEqual(link['class'], 'button active' if active else 'button secondary')
            self.assertEqual(link.get('aria-current'), 'page' if active else None)

    def test_all_admin_views_share_theme_and_superuser_policy(self):
        urls = list(self.page_urls())
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'admin/base_site.html')
                self.assertContains(response, 'catalog/admin.css')
                self.assertNotContains(response, 'admin/css/dark_mode.css')
                self.assertNotContains(response, 'admin/js/theme.js')
                name = resolve(url).url_name
                expected = None
                for model in ('catalog_medicine', 'catalog_batch', 'auth_user', 'catalog_shift', 'catalog_sale', 'catalog_stocktransfer'):
                    if name.startswith(model + '_'):
                        action = 'add' if name in ('catalog_medicine_add', 'catalog_batch_add') else 'changelist'
                        expected = reverse(f'admin:{model}_{action}')
                self.assert_navigation(response, expected)
        self.client.force_login(self.worker)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_validation_inline_search_filters_and_save(self):
        url = reverse('admin:catalog_medicine_add')
        response = self.client.post(url, {'placements-TOTAL_FORMS': '1', 'placements-INITIAL_FORMS': '0'})
        self.assertContains(response, 'errorlist')
        self.assertContains(response, 'catalog/admin.css')
        self.assertContains(response, 'placements-0-batch')
        self.assert_navigation(response, url)
        batch_url = reverse('admin:catalog_batch_add')
        response = self.client.post(batch_url, {'medicine': self.medicine.pk, 'number': 'Theme batch', 'expires_on': '2027-01-01', '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        batch = self.medicine.batches.get(number='Theme batch')
        response = self.client.post(reverse('admin:catalog_batch_change', args=[batch.pk]), {'expires_on': '2028-01-01', '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        batch.refresh_from_db()
        self.assertEqual(str(batch.expires_on), '2028-01-01')
        response = self.client.get(reverse('admin:catalog_medicine_changelist'), {'q': 'Theme', 'is_demo__exact': '0'})
        self.assertContains(response, 'Theme medicine')
        self.assert_navigation(response, reverse('admin:catalog_medicine_changelist'))
        for model in ('catalog_shift', 'catalog_sale', 'catalog_stocktransfer'):
            self.assertEqual(self.client.get(reverse(f'admin:{model}_add')).status_code, 403)

    def test_popup_and_bulk_delete_confirmation_use_shared_theme(self):
        response = self.client.get(reverse('admin:catalog_batch_add'), {'_popup': '1'})
        self.assertContains(response, 'catalog/admin.css')
        self.assertNotContains(response, 'aria-label="Boshqaruv amallari"')
        response = self.client.post(reverse('admin:catalog_medicine_changelist'), {
            'action': 'delete_selected', '_selected_action': [self.medicine.pk],
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/delete_selected_confirmation.html')
        self.assertContains(response, 'catalog/admin.css')
        self.assertTrue(Medicine.objects.filter(pk=self.medicine.pk).exists())
        self.assert_navigation(response, reverse('admin:catalog_medicine_changelist'))
