import re
from html.parser import HTMLParser

from django.contrib.auth.models import Group
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.translation import override

from .test_admin_theme import AdminThemeTests


class VisibleText(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.parts = []
        self.hidden = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        attrs = dict(attrs)
        for key in ('title', 'aria-label', 'placeholder'):
            if key in attrs:
                self.parts.append(attrs[key])
        if tag == 'input' and attrs.get('type') in ('submit', 'button'):
            self.parts.append(attrs.get('value', ''))

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden -= 1

    def handle_data(self, text):
        if not self.hidden and text.strip():
            self.parts.append(text.strip())


class AdminLanguageTests(TestCase):
    setUp = AdminThemeTests.setUp
    page_urls = AdminThemeTests.page_urls

    def test_both_languages_on_all_admin_and_workflow_pages(self):
        urls = list(self.page_urls()) + [
            reverse('catalog:shifts'), reverse('catalog:schedule_create'),
            reverse('catalog:shift_detail', args=[self.shift.pk]),
            reverse('catalog:create'), reverse('catalog:edit', args=[self.medicine.pk]),
            reverse('catalog:sale_cancel', args=[self.sale.pk]),
            reverse('catalog:transfer', args=[self.medicine.pk]),
        ]
        for language, save in [('uz', 'Saqlash'), ('ru', 'Сохранить')]:
            self.client.cookies['django_language'] = language
            for index, url in enumerate(urls):
                with self.subTest(language=language, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers['Content-Language'], language)
                    self.assertContains(response, 'O‘zbekcha')
                    self.assertContains(response, 'Русский')
                    text = '\n'.join(VisibleText(response.content.decode()).parts)
                    for word in ['Save', 'Delete', 'Users', 'Batch', 'Choose', 'History', 'Select', 'object', 'Can']:
                        self.assertIsNone(re.search(r'\b'+word+r'\b', text), (url, text))
                    if language == 'ru':
                        for word in ['Saqlash', 'Dorilar', 'Partiyalar', 'Smenalar', 'Qoldiq', 'Boshlangan']:
                            self.assertNotIn(word, text)
            self.assertContains(self.client.get(reverse('admin:catalog_medicine_change', args=[self.medicine.pk])), 'Theme medicine')
            self.assertContains(self.client.get(reverse('admin:catalog_medicine_add')), f'value="{save}"')
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.name, 'Theme medicine')

    def test_switch_preserves_path_query_and_next_requests(self):
        url = reverse('admin:catalog_medicine_changelist') + '?q=Theme&is_demo__exact=0'
        for language in ['ru', 'uz']:
            response = self.client.post(reverse('set_language'), {'language': language, 'next': url})
            self.assertRedirects(response, url)
            self.assertEqual(response.cookies['django_language'].value, language)
            self.assertEqual(self.client.get(reverse('admin:auth_user_add')).headers['Content-Language'], language)
        response = self.client.post(reverse('set_language'), {'language': 'ru', 'next': 'https://evil.example/'})
        self.assertNotIn('evil.example', response.url)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('set_language'), {'language': 'ru', 'next': url}).status_code, 403)

    def test_validation_success_delete_login_and_javascript(self):
        for language, required, confirmed, added in [('uz', 'Bu maydonni to‘ldiring.', 'Ha, tasdiqlayman', 'muvaffaqiyatli qo‘shildi'), ('ru', 'Заполните это поле.', 'Да, я уверен', 'успешно добавлен')]:
            self.client.cookies['django_language'] = language
            response = self.client.post(reverse('admin:catalog_medicine_add'), {'placements-TOTAL_FORMS': 1, 'placements-INITIAL_FORMS': 0})
            self.assertContains(response, required)
            response = self.client.post(reverse('admin:catalog_batch_add'), {'medicine': self.medicine.pk, 'number': 'Batch input '+language, 'expires_on': '2028-01-01', '_save': '1'}, follow=True)
            self.assertContains(response, added)
            response = self.client.post(reverse('admin:auth_group_changelist'), {'action': 'delete_selected', '_selected_action': [Group.objects.create(name='Test '+language).pk]})
            self.assertContains(response, confirmed)
            response = self.client.get(reverse('admin:jsi18n'))
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('"Choose all %s": "Choose all %s"', response.content.decode())
            anonymous = Client()
            anonymous.cookies['django_language'] = language
            response = anonymous.get(reverse('admin:login'))
            self.assertEqual(response.headers['Content-Language'], language)
            self.assertContains(response, 'Русский')

    def test_navigation_and_medicine_sections_are_expanded(self):
        response = self.client.get(reverse('admin:index'))
        self.assertNotContains(response, '<details class="management-menu"')
        response = self.client.get(reverse('admin:catalog_medicine_add'))
        self.assertNotContains(response, 'class="module aligned collapse"')
        self.assertNotContains(response, 'nav-group')
        self.assertNotContains(response, 'quick-actions')
        self.assertLess(response.content.index(b'id_name'), response.content.index(b'id_alternative_names'))
        self.assertLess(response.content.index(b'id_alternative_names'), response.content.index(b'id_price'))

    def test_placement_snapshot_is_language_independent(self):
        with override('uz'):
            stable = self.place.location_key
        with override('ru'):
            self.assertEqual(self.place.location_key, stable)
            self.assertIn('полка', str(self.place))
            self.assertNotIn('polka', str(self.place))
