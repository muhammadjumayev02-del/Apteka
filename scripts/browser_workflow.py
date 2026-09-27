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
from catalog.models import Medicine, Placement, Batch, Sale, ShiftSchedule
from playwright.sync_api import sync_playwright, expect

class BrowserCheck(StaticLiveServerTestCase):
    def test_flow(self):
        owner = User.objects.create_superuser('browser-admin', password='Browser-test-1234!')
        ShiftSchedule.objects.create(user=owner, planned_start=timezone.now(), planned_end=timezone.now()+timedelta(hours=8))
        med=Medicine.objects.create(name='Browser sample', dosage='10 mg', form='Tablet', package_size='20', price='1250.50', barcode='0001234567890', is_demo=True)
        batch=Batch.objects.create(medicine=med,number='BR',expires_on=timezone.localdate()+timedelta(days=20))
        place=Placement.objects.create(medicine=med,batch=batch,department='A',shelf=1,row=1,quantity=10)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True, executable_path='/usr/bin/google-chrome')
            page=browser.new_page(locale='uz-UZ')
            page.goto(self.live_server_url+'/kirish/')
            page.locator('#id_username').fill('browser-admin')
            page.locator('#id_password').fill('Browser-test-1234!')
            page.get_by_role('button', name='Kirish →', exact=True).click()
            page.wait_for_url(self.live_server_url+'/')
            page.goto(self.live_server_url+'/smenalar/')
            page.locator('button').filter(has_text='Smenani boshlash').first.click()
            page.goto(self.live_server_url+'/')
            page.locator('#query').fill('0001234567890')
            page.locator('#query').press('Enter')
            expect(page.locator('.medicine-card')).to_have_count(1)
            page.get_by_role('link', name='Sotuv qilish', exact=True).click()
            page.locator('#id_payment_method').select_option('cash')
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
            # Exercise a multi-line receipt through the actual cart UI.
            for count in ('1','2'):
                page.goto(self.live_server_url+f'/dorilar/{med.pk}/sotish/')
                page.locator('#id_payment_method').select_option('cash')
                page.locator('#id_placement').select_option(str(place.pk))
                page.locator('#id_quantity').fill(count)
                page.get_by_role('button', name='Savatga qo‘shish', exact=True).click()
            expect(page.locator('tbody tr')).to_have_count(2)
            page.get_by_role('button', name='Sotuvni tasdiqlash', exact=True).click()
            page.get_by_role('link', name='browser-admin', exact=True).click()
            page.get_by_role('link', name='Sotuvni bekor qilish va qoldiqni qaytarish').first.click()
            page.get_by_role('button', name='Ha, sotuvni bekor qilish', exact=True).click()
            page.goto(self.live_server_url+'/hisobotlar/')
            expect(page.locator('h1')).to_have_text('Hisobotlar')
            page.goto(self.live_server_url+'/admin/catalog/batch/')
            expect(page.locator('.dashboard-actions a.active')).to_have_count(1)
            page.get_by_role('button',name='Русский',exact=True).click()
            expect(page.locator('html')).to_have_attribute('lang', 'ru')
            expect(page.locator('.dashboard-actions a.active')).to_have_count(1)
            page.screenshot(path='/tmp/apteka-browser-ru.png',full_page=True)
            page.get_by_role('button', name='English', exact=True).click()
            expect(page.locator('html')).to_have_attribute('lang', 'en')
            page.goto(self.live_server_url+f'/dorilar/{med.pk}/sotish/')
            expect(page.locator('h1')).to_have_text('Make a sale')
            page.locator('#id_payment_method').select_option('card')
            page.locator('#id_quantity').fill('2')
            expect(page.locator('#sale-total')).to_have_text('2501.00')
            page.goto(self.live_server_url+'/hisobotlar/')
            expect(page.locator('h1')).to_have_text('Reports')
            expect(page.get_by_role('heading', name='Cash revenue')).to_be_visible()
            page.get_by_role('button', name='O‘zbekcha', exact=True).click()
            expect(page.locator('h1')).to_have_text('Hisobotlar')
            browser.close()
        place.refresh_from_db()
        self.assertEqual(place.quantity, 10)
        self.assertEqual(Sale.objects.count(), 3)
        self.assertFalse(Sale.objects.filter(cancelled_at__isnull=True).exists())

raise SystemExit(DiscoverRunner(verbosity=2).run_tests(['__main__.BrowserCheck']))
