import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test.runner import DiscoverRunner
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from catalog.models import Medicine, Placement, Batch, Sale
from playwright.sync_api import sync_playwright, expect

class BrowserCheck(StaticLiveServerTestCase):
    def test_flow(self):
        User.objects.create_superuser('browser-admin', password='Browser-test-1234!')
        med=Medicine.objects.create(name='Browser sample', dosage='10 mg', form='Tablet', package_size='20', price='1250.50')
        batch=Batch.objects.create(medicine=med,number='BR',expires_on=timezone.localdate()+timedelta(days=20))
        place=Placement.objects.create(medicine=med,batch=batch,department='A',shelf=1,row=1,quantity=10)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True, executable_path='/usr/bin/google-chrome')
            page=browser.new_page()
            page.goto(self.live_server_url+'/kirish/')
            page.locator('#id_username').fill('browser-admin')
            page.locator('#id_password').fill('Browser-test-1234!')
            page.get_by_role('button', name='Kirish →', exact=True).click()
            page.wait_for_url(self.live_server_url+'/')
            page.goto(self.live_server_url+'/smenalar/')
            page.locator('button').filter(has_text='Smenani boshlash').first.click()
            page.goto(self.live_server_url+f'/dorilar/{med.pk}/sotish/')
            page.locator('#id_placement').select_option(str(place.pk))
            page.locator('#id_quantity').fill('3')
            assert page.locator('#sale-total').inner_text()=='3751,50'
            page.get_by_role('button',name='Jami narxni ko‘rish').click()
            page.get_by_role('button',name='Sotuvni tasdiqlash').click()
            cancel_url = page.get_by_role('link', name='Sotuvni bekor qilish va qoldiqni qaytarish').get_attribute('href')
            page.goto(self.live_server_url+f'/dorilar/{med.pk}/')
            expect(page.locator('.total')).to_have_text('7 pachka')
            page.goto(self.live_server_url+cancel_url)
            page.get_by_role('button', name='Ha, sotuvni bekor qilish', exact=True).click()
            expect(page.get_by_text('Sotuv bekor qilindi. Pachkalar qoldiqqa qaytarildi.')).to_be_visible()
            page.goto(self.live_server_url+'/admin/catalog/batch/')
            expect(page.locator('.dashboard-actions a.active')).to_have_count(1)
            page.get_by_role('button',name='Русский',exact=True).click()
            expect(page.locator('html')).to_have_attribute('lang', 'ru')
            expect(page.locator('.dashboard-actions a.active')).to_have_count(1)
            page.screenshot(path='/tmp/apteka-browser-ru.png',full_page=True)
            browser.close()
        place.refresh_from_db()
        self.assertEqual(place.quantity, 10)
        self.assertIsNotNone(Sale.objects.get().cancelled_at)

raise SystemExit(DiscoverRunner(verbosity=2).run_tests(['__main__.BrowserCheck']))
