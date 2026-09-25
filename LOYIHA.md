# Apteka: ishga tayyor Django loyiha

## Papkalar tuzilmasi

```text
Apteka/
├── .gitignore
├── README.md
├── catalog/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── seed_demo.py
│   │       └── setup_roles.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
├── static/
│   └── catalog/
│       ├── app.css
│       └── app.js
└── templates/
    ├── 403.html
    ├── 404.html
    ├── base.html
    ├── catalog/
    │   ├── detail.html
    │   ├── edit.html
    │   ├── home.html
    │   └── results.html
    └── registration/
        └── login.html
```

## Har bir faylning to‘liq kodi

### `requirements.txt`

```text
Django==5.2.17
```

### `.gitignore`

```text
.venv/
__pycache__/
*.py[cod]
db.sqlite3
.env
staticfiles/
```

### `manage.py`

```python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
```

### `config/__init__.py`

Bo‘sh fayl yarating.

### `config/settings.py`

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-development-only-apteka-key")
if not DEBUG and SECRET_KEY == "local-development-only-apteka-key":
    raise RuntimeError("DJANGO_SECRET_KEY muhit o‘zgaruvchisini belgilang.")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,[::1]").split(",")
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "catalog.apps.CatalogConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "catalog:home"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
```

### `config/urls.py`

```python
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from catalog.forms import UzbekAuthenticationForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path("kirish/", LoginView.as_view(authentication_form=UzbekAuthenticationForm), name="login"),
    path("chiqish/", LogoutView.as_view(), name="logout"),
    path("", include("catalog.urls")),
]
```

### `config/wsgi.py`

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
```

### `catalog/__init__.py`

Bo‘sh fayl yarating.

### `catalog/admin.py`

```python
from django.contrib import admin
from .models import Medicine, Placement


class PlacementInline(admin.TabularInline):
    model = Placement
    extra = 1
    min_num = 1
    validate_min = True


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ["name", "dosage", "form", "price", "is_demo", "updated_at"]
    search_fields = ["name", "active_ingredients"]
    list_filter = ["is_demo", "form"]
    readonly_fields = ["updated_at"]
    inlines = [PlacementInline]


admin.site.site_header = "Apteka boshqaruvi"
admin.site.site_title = "Apteka"
admin.site.index_title = "Boshqaruv paneli"
```

### `catalog/apps.py`

```python
from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"
    verbose_name = "Dorilar katalogi"
```

### `catalog/forms.py`

```python
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.forms import inlineformset_factory
from .models import Medicine, Placement


class UzbekAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Foydalanuvchi nomi", widget=forms.TextInput(attrs={"autofocus": True}))
    password = forms.CharField(label="Parol", strip=False, widget=forms.PasswordInput)
    error_messages = {
        "invalid_login": "Foydalanuvchi nomi yoki parol noto‘g‘ri.",
        "inactive": "Bu hisob faol emas.",
    }


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ["name", "dosage", "form", "price", "active_ingredients", "indications",
                  "source", "reviewed_on", "is_demo"]
        widgets = {
            "reviewed_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            **{field: forms.Textarea(attrs={"rows": 3})
               for field in ["active_ingredients", "indications", "source"]},
        }


PlacementFormSet = inlineformset_factory(
    Medicine, Placement, fields=["department", "shelf", "row", "quantity"],
    extra=1, can_delete=True, min_num=1, validate_min=True,
    max_num=100, validate_max=True,
)
```

### `catalog/management/__init__.py`

Bo‘sh fayl yarating.

### `catalog/management/commands/__init__.py`

Bo‘sh fayl yarating.

### `catalog/management/commands/seed_demo.py`

```python
from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import Medicine, Placement


class Command(BaseCommand):
    help = "Tibbiy ma’lumotsiz uchta xayoliy namuna qo‘shadi."

    @transaction.atomic
    def handle(self, *args, **options):
        for name, dosage, form, price, quantity in [
            ("Namuna A — xayoliy", "10 mg (namuna)", "Tabletka", "12000", 24),
            ("Namuna B — xayoliy", "5 mg / ml (namuna)", "Sirop", "18000", 8),
            ("Namuna C — xayoliy", "20 mg (namuna)", "Kapsula", "24000", 0),
        ]:
            medicine, created = Medicine.objects.get_or_create(name=name, is_demo=True, defaults={
                "dosage": dosage, "form": form, "price": price,
            })
            if created:
                Placement.objects.create(medicine=medicine, department="Namuna bo‘limi",
                                         shelf=3, row=2, quantity=quantity)
                if name.startswith("Namuna A"):
                    Placement.objects.create(medicine=medicine, department="Namuna zaxirasi",
                                             shelf=1, row=1, quantity=6)
        self.stdout.write(self.style.SUCCESS("Xayoliy namunalar tayyor. Tibbiy ma’lumot kiritilmadi."))
```

### `catalog/management/commands/setup_roles.py`

```python
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Aptekachi va Vakolatli xodim guruhlarini yaratadi."

    def handle(self, *args, **options):
        reader, _ = Group.objects.get_or_create(name="Aptekachi")
        reader.permissions.set(Permission.objects.filter(
            content_type__app_label="catalog", codename__in=["view_medicine", "view_placement"]))
        editor, _ = Group.objects.get_or_create(name="Vakolatli xodim")
        editor.permissions.set(Permission.objects.filter(content_type__app_label="catalog"))
        self.stdout.write(self.style.SUCCESS("Xodim guruhlari tayyor."))
```

### `catalog/migrations/0001_initial.py`

```python
# Generated by Django 5.2.17 on 2026-09-23 09:52

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Medicine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=180, verbose_name='Savdo nomi')),
                ('dosage', models.CharField(max_length=80, verbose_name='Dozasi')),
                ('form', models.CharField(max_length=80, verbose_name='Dori shakli')),
                ('active_ingredients', models.TextField(blank=True, verbose_name='Tarkibi / faol moddalar')),
                ('indications', models.TextField(blank=True, verbose_name='Rasmiy yo‘riqnomaga ko‘ra qo‘llanishi')),
                ('source', models.TextField(blank=True, verbose_name='Manba (yo‘riqnoma nomi, versiyasi yoki havola)')),
                ('reviewed_on', models.DateField(blank=True, null=True, verbose_name='Tibbiy ma’lumot tekshirilgan sana')),
                ('price', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Narxi (so‘m)')),
                ('is_demo', models.BooleanField(default=False, verbose_name='Xayoliy namuna')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Oxirgi yangilanish')),
                ('search_text', models.TextField(editable=False)),
            ],
            options={
                'verbose_name': 'Dori',
                'verbose_name_plural': 'Dorilar',
                'ordering': ['name', 'pk'],
                'constraints': [models.CheckConstraint(condition=models.Q(('price__gte', 0)), name='price_nonnegative')],
            },
        ),
        migrations.CreateModel(
            name='Placement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('department', models.CharField(max_length=120, verbose_name='Bo‘lim')),
                ('shelf', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='Polka')),
                ('row', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='Qator')),
                ('quantity', models.PositiveIntegerField(default=0, verbose_name='Mavjud soni')),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='placements', to='catalog.medicine')),
            ],
            options={
                'verbose_name': 'Joylashuv',
                'verbose_name_plural': 'Joylashuvlar',
                'ordering': ['department', 'shelf', 'row'],
                'constraints': [models.UniqueConstraint(fields=('medicine', 'department', 'shelf', 'row'), name='unique_placement'), models.CheckConstraint(condition=models.Q(('row__gte', 1), ('shelf__gte', 1)), name='positive_coordinates')],
            },
        ),
    ]
```

### `catalog/migrations/__init__.py`

Bo‘sh fayl yarating.

### `catalog/models.py`

```python
import unicodedata
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


def normalize(text):
    # SQLite uchun kirill, lotin va turli apostroflarni bir xilda qidirish.
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(text.translate(str.maketrans({c: "'" for c in "‘’ʻʼ`"})).split())


class Medicine(models.Model):
    name = models.CharField("Savdo nomi", max_length=180)
    dosage = models.CharField("Dozasi", max_length=80)
    form = models.CharField("Dori shakli", max_length=80)
    active_ingredients = models.TextField("Tarkibi / faol moddalar", blank=True)
    indications = models.TextField("Rasmiy yo‘riqnomaga ko‘ra qo‘llanishi", blank=True)
    source = models.TextField("Manba (yo‘riqnoma nomi, versiyasi yoki havola)", blank=True)
    reviewed_on = models.DateField("Tibbiy ma’lumot tekshirilgan sana", null=True, blank=True)
    price = models.DecimalField("Narxi (so‘m)", max_digits=12, decimal_places=2,
                                validators=[MinValueValidator(0)])
    is_demo = models.BooleanField("Xayoliy namuna", default=False)
    updated_at = models.DateTimeField("Oxirgi yangilanish", auto_now=True)
    search_text = models.TextField(editable=False)

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = "Dori"
        verbose_name_plural = "Dorilar"
        constraints = [models.CheckConstraint(condition=models.Q(price__gte=0), name="price_nonnegative")]

    def __str__(self):
        return f"{self.name} · {self.dosage}"

    def get_absolute_url(self):
        return reverse("catalog:detail", args=[self.pk])

    def clean(self):
        errors = {}
        if self.active_ingredients.strip() or self.indications.strip():
            if not self.source.strip():
                errors["source"] = "Tibbiy ma’lumot uchun rasmiy manbani kiriting."
            if not self.reviewed_on:
                errors["reviewed_on"] = "Tekshirilgan sanani kiriting."
        if self.reviewed_on and self.reviewed_on > timezone.localdate():
            errors["reviewed_on"] = "Sana kelajakda bo‘lishi mumkin emas."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.search_text = normalize(f"{self.name} {self.active_ingredients}")
        self.full_clean()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"search_text", "updated_at"}
        super().save(*args, **kwargs)


class Placement(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="placements")
    department = models.CharField("Bo‘lim", max_length=120)
    shelf = models.PositiveSmallIntegerField("Polka", validators=[MinValueValidator(1)])
    row = models.PositiveSmallIntegerField("Qator", validators=[MinValueValidator(1)])
    quantity = models.PositiveIntegerField("Mavjud soni", default=0)

    class Meta:
        ordering = ["department", "shelf", "row"]
        verbose_name = "Joylashuv"
        verbose_name_plural = "Joylashuvlar"
        constraints = [
            models.UniqueConstraint(fields=["medicine", "department", "shelf", "row"], name="unique_placement"),
            models.CheckConstraint(condition=models.Q(shelf__gte=1, row__gte=1), name="positive_coordinates"),
        ]

    def __str__(self):
        return f"{self.department} → {self.shelf}-polka → {self.row}-qator"
```

### `catalog/tests.py`

```python
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Medicine, Placement


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", verbosity=0)
        cls.reader = User.objects.create_user("reader", password="test-password-739")
        cls.editor = User.objects.create_user("editor", password="test-password-739")
        cls.reader.groups.add(Group.objects.get(name="Aptekachi"))
        cls.editor.groups.add(Group.objects.get(name="Vakolatli xodim"))
        cls.medicine = Medicine.objects.create(
            name="Xayoliy Alfa", dosage="10 mg (namuna)", form="Tabletka", price="12000",
            active_ingredients="Xayoliy МОДДА (haqiqiy emas)", is_demo=True,
            source="Avtomatik test uchun xayoliy manba; rasmiy yo‘riqnoma emas",
            reviewed_on=timezone.localdate(),
        )
        cls.place = Placement.objects.create(medicine=cls.medicine, department="Namuna bo‘limi",
                                              shelf=3, row=2, quantity=4)
        Placement.objects.create(medicine=cls.medicine, department="Zaxira",
                                 shelf=1, row=1, quantity=6)

    def setUp(self):
        self.client.force_login(self.reader)

    def payload(self):
        return {
            "name": "Yangilangan xayoliy dori", "dosage": "20 mg", "form": "Sirop",
            "price": "15000.50", "active_ingredients": "", "indications": "",
            "source": "", "reviewed_on": "", "is_demo": "on",
            "places-TOTAL_FORMS": "2", "places-INITIAL_FORMS": "2",
            "places-0-id": str(self.place.pk), "places-0-department": "Yangi bo‘lim",
            "places-0-shelf": "5", "places-0-row": "4", "places-0-quantity": "12",
            "places-1-id": str(self.medicine.placements.exclude(pk=self.place.pk).get().pk),
            "places-1-department": "Zaxira", "places-1-shelf": "1",
            "places-1-row": "1", "places-1-quantity": "6",
        }

    def test_partial_name_and_unicode_ingredient_search(self):
        for query in ["ALF", "модд", "xayoliy alfa"]:
            response = self.client.get(reverse("catalog:home"), {"q": query, "partial": "1"})
            self.assertContains(response, self.medicine.name)
            self.assertContains(response, "10 dona")
        self.assertContains(self.client.get("/", {"q": "topilmaydi"}), "Dori topilmadi")

    def test_all_locations_and_total_are_shown(self):
        response = self.client.get(self.medicine.get_absolute_url())
        self.assertContains(response, "Namuna bo‘limi → 3-polka → 2-qator")
        self.assertContains(response, "Zaxira → 1-polka → 1-qator")
        self.assertContains(response, "10 dona")
        self.assertContains(response, "Qo‘llashdan oldin rasmiy yo‘riqnoma")
        self.assertContains(response, "XAYOLIY NAMUNA")

    def test_anonymous_cannot_read_or_write(self):
        self.client.logout()
        for url in ["/", "/?partial=1", self.medicine.get_absolute_url(), reverse("catalog:create")]:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_user_without_role_is_forbidden(self):
        self.client.force_login(User.objects.create_user("outsider"))
        self.assertEqual(self.client.get("/").status_code, 403)

    def test_reader_cannot_create_edit_or_use_admin(self):
        for url in [reverse("catalog:create"), reverse("catalog:edit", args=[self.medicine.pk])]:
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, self.payload()).status_code, 403)
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.name, "Xayoliy Alfa")
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_editor_can_update_price_stock_and_location(self):
        self.client.force_login(self.editor)
        response = self.client.post(reverse("catalog:edit", args=[self.medicine.pk]), self.payload())
        self.assertRedirects(response, self.medicine.get_absolute_url())
        self.medicine.refresh_from_db()
        self.place.refresh_from_db()
        self.assertEqual(self.medicine.price, Decimal("15000.50"))
        self.assertEqual((self.place.department, self.place.shelf, self.place.row, self.place.quantity),
                         ("Yangi bo‘lim", 5, 4, 12))
        self.assertContains(self.client.get("/", {"q": "yangilangan"}), self.medicine.name)
        self.assertNotContains(self.client.get("/", {"q": "alfa"}), self.medicine.name)

    def test_editor_can_create_with_two_locations(self):
        self.client.force_login(self.editor)
        data = self.payload()
        data["places-INITIAL_FORMS"] = "0"
        data.pop("places-0-id")
        data.pop("places-1-id")
        response = self.client.post(reverse("catalog:create"), data)
        medicine = Medicine.objects.get(name=data["name"])
        self.assertRedirects(response, medicine.get_absolute_url())
        self.assertEqual(medicine.placements.count(), 2)

    def test_invalid_stock_does_not_save_medicine(self):
        self.client.force_login(self.editor)
        data = self.payload()
        data["places-0-quantity"] = "-1"
        response = self.client.post(reverse("catalog:edit", args=[self.medicine.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["placements"].errors[0])
        self.medicine.refresh_from_db()
        self.assertEqual(self.medicine.name, "Xayoliy Alfa")

    def test_clinical_text_requires_source_and_date(self):
        medicine = Medicine(name="Sinov", dosage="Sinov", form="Sinov", price=0,
                            indications="Xayoliy test matni")
        with self.assertRaises(ValidationError) as error:
            medicine.save()
        self.assertIn("source", error.exception.message_dict)
        self.assertIn("reviewed_on", error.exception.message_dict)
        medicine.source = "Xayoliy test manbasi"
        medicine.reviewed_on = timezone.localdate() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            medicine.save()

    def test_duplicate_and_missing_locations_are_rejected(self):
        self.client.force_login(self.editor)
        data = self.payload()
        for field in ["department", "shelf", "row"]:
            data[f"places-1-{field}"] = data[f"places-0-{field}"]
        response = self.client.post(reverse("catalog:edit", args=[self.medicine.pk]), data)
        self.assertTrue(response.context["placements"].non_form_errors())
        data = self.payload()
        data.update({"places-0-DELETE": "on", "places-1-DELETE": "on"})
        response = self.client.post(reverse("catalog:edit", args=[self.medicine.pk]), data)
        self.assertTrue(response.context["placements"].non_form_errors())

    def test_editor_cannot_modify_another_medicines_placement(self):
        self.client.force_login(self.editor)
        other = Medicine.objects.create(name="Boshqa", dosage="Sinov", form="Sinov", price=0)
        foreign = Placement.objects.create(medicine=other, department="Boshqa", shelf=1, row=1, quantity=9)
        data = self.payload()
        data["places-0-id"] = str(foreign.pk)
        self.client.post(reverse("catalog:edit", args=[self.medicine.pk]), data)
        foreign.refresh_from_db()
        self.assertEqual(foreign.quantity, 9)
        self.assertEqual(foreign.medicine_id, other.pk)

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.editor)
        self.assertEqual(client.post(reverse("catalog:create"), self.payload()).status_code, 403)

    def test_login_editor_form_and_logout(self):
        self.client.logout()
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Foydalanuvchi nomi")
        response = self.client.post(reverse("login"), {
            "username": "editor", "password": "test-password-739",
        })
        self.assertRedirects(response, "/")
        self.assertContains(self.client.get(reverse("catalog:create")), "places-TOTAL_FORMS")
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_editor_can_remove_one_location(self):
        self.client.force_login(self.editor)
        data = self.payload()
        data["places-1-DELETE"] = "on"
        response = self.client.post(reverse("catalog:edit", args=[self.medicine.pk]), data)
        self.assertRedirects(response, self.medicine.get_absolute_url())
        self.assertEqual(self.medicine.placements.count(), 1)

    def test_demo_command_is_idempotent_and_has_no_medical_claims(self):
        call_command("seed_demo")
        count = Medicine.objects.count()
        call_command("seed_demo")
        self.assertEqual(Medicine.objects.count(), count)
        for medicine in Medicine.objects.filter(name__startswith="Namuna"):
            self.assertTrue(medicine.is_demo)
            self.assertEqual(medicine.active_ingredients, "")
            self.assertEqual(medicine.indications, "")

    def test_pagination_and_escaping(self):
        self.medicine.name = "<script>alert(1)</script>"
        self.medicine.save()
        response = self.client.get("/")
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")
        for index in range(21):
            Medicine.objects.create(name=f"Sinov {index}", dosage="Sinov", form="Sinov", price=0)
        response = self.client.get("/", {"page": "2"})
        self.assertEqual(len(response.context["page_obj"]), 2)
```

### `catalog/urls.py`

```python
from django.urls import path
from . import views

app_name = "catalog"
urlpatterns = [
    path("", views.home, name="home"),
    path("dorilar/yangi/", views.edit, name="create"),
    path("dorilar/<int:pk>/", views.detail, name="detail"),
    path("dorilar/<int:pk>/tahrirlash/", views.edit, name="edit"),
]
```

### `catalog/views.py`

```python
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from .forms import MedicineForm, PlacementFormSet
from .models import Medicine, normalize


def medicines():
    return Medicine.objects.annotate(total=Sum("placements__quantity", default=0)).order_by("name", "pk")


@login_required
@permission_required("catalog.view_medicine", raise_exception=True)
@require_GET
def home(request):
    query = request.GET.get("q", "").strip()[:180]
    items = medicines()
    for word in normalize(query).split():
        items = items.filter(search_text__contains=word)
    page = Paginator(items, 20).get_page(request.GET.get("page"))
    template = "catalog/results.html" if request.GET.get("partial") == "1" else "catalog/home.html"
    return render(request, template, {"page_obj": page, "q": query})


@login_required
@permission_required("catalog.view_medicine", raise_exception=True)
@require_GET
def detail(request, pk):
    medicine = get_object_or_404(medicines().prefetch_related("placements"), pk=pk)
    return render(request, "catalog/detail.html", {"medicine": medicine})


@login_required
@permission_required([
    "catalog.view_medicine", "catalog.add_medicine", "catalog.change_medicine",
    "catalog.add_placement", "catalog.change_placement", "catalog.delete_placement",
], raise_exception=True)
@require_http_methods(["GET", "POST"])
def edit(request, pk=None):
    with transaction.atomic():
        medicine = get_object_or_404(Medicine.objects.select_for_update(), pk=pk) if pk else Medicine()
        form = MedicineForm(request.POST if request.method == "POST" else None, instance=medicine)
        placements = PlacementFormSet(request.POST if request.method == "POST" else None,
                                      instance=medicine, prefix="places")
        if request.method == "POST":
            valid_form = form.is_valid()
            valid_places = placements.is_valid()
            if valid_form and valid_places:
                form.save()
                placements.save()
                messages.success(request, "Dori ma’lumotlari saqlandi.")
                return redirect(medicine)
    return render(request, "catalog/edit.html", {"form": form, "placements": placements, "medicine": medicine})
```

### `templates/403.html`

```html
{% extends 'base.html' %}
{% block content %}<section class="panel"><h1>Ruxsat yetarli emas</h1><p>Kerakli xodim guruhiga qo‘shish uchun administratorga murojaat qiling.</p><a href="{% url 'catalog:home' %}">Bosh sahifaga qaytish</a></section>{% endblock %}
```

### `templates/404.html`

```html
{% extends 'base.html' %}
{% block content %}<section class="panel"><h1>Sahifa topilmadi</h1><a href="{% url 'catalog:home' %}">Dori qidirishga qaytish</a></section>{% endblock %}
```

### `templates/base.html`

```html
{% load static %}
<!doctype html>
<html lang="uz">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Apteka · Dori qidirish{% endblock %}</title>
  <link rel="stylesheet" href="{% static 'catalog/app.css' %}">
  <script src="{% static 'catalog/app.js' %}" defer></script>
</head>
<body>
<header class="header">
  <a class="brand" href="{% url 'catalog:home' %}"><span class="logo">+</span> apteka<span class="brand-dot">.</span></a>
  <nav aria-label="Asosiy menyu">
    {% if user.is_authenticated %}
      {% if perms.catalog.change_medicine %}<a href="{% url 'catalog:create' %}">+ Dori qo‘shish</a>{% endif %}
      {% if user.is_staff %}<a href="{% url 'admin:index' %}">Boshqaruv</a>{% endif %}
      <span class="username">{{ user.username }}</span>
      <form method="post" action="{% url 'logout' %}">{% csrf_token %}<button class="text-button">Chiqish</button></form>
    {% endif %}
  </nav>
</header>
<main class="container">
  {% for message in messages %}<p class="notice" role="status">{{ message }}</p>{% endfor %}
  {% block content %}{% endblock %}
</main>
<footer class="container footer">Apteka ichki katalogi <span>Kerakli dori. Aniq joylashuv.</span></footer>
</body>
</html>
```

### `templates/catalog/detail.html`

```html
{% extends 'base.html' %}
{% block title %}{{ medicine.name }} · Apteka{% endblock %}
{% block content %}
<a class="back" href="{% url 'catalog:home' %}">← Qidiruvga qaytish</a>
{% if medicine.is_demo %}<p class="demo-banner">XAYOLIY NAMUNA. Bu haqiqiy dori emas; nomi, dozasi va narxi faqat saytni sinash uchun.</p>{% endif %}
<div class="detail-heading"><div><p class="eyebrow">DORI MA’LUMOTLARI</p><h1>{{ medicine.name }}</h1><p class="muted">{{ medicine.dosage }} · {{ medicine.form }}</p></div>
{% if perms.catalog.change_medicine %}<a class="button secondary" href="{% url 'catalog:edit' medicine.pk %}">Tahrirlash</a>{% endif %}</div>
<div class="detail-grid">
  <section class="location-panel"><p class="eyebrow">APTEKADAGI JOYLASHUVI</p><h2>Qayerdan topish mumkin?</h2>
    {% for place in medicine.placements.all %}<div class="location"><strong>{{ place.department }} → {{ place.shelf }}-polka → {{ place.row }}-qator</strong><span>{{ place.quantity }} dona{% if not place.quantity %} · Bu joyda qolmagan{% endif %}</span></div>{% empty %}<p>Joylashuv hali kiritilmagan.</p>{% endfor %}
  </section>
  <section class="panel summary"><p class="muted">Bir dona narxi</p><h2>{{ medicine.price|floatformat:2 }} <small>so‘m</small></h2><hr><p class="muted">Jami mavjud</p><strong class="total">{{ medicine.total }} dona</strong>{% if not medicine.total %}<p>Hozir omborda mavjud emas.</p>{% endif %}</section>
</div>
<section class="panel clinical">
  <h2>Yo‘riqnoma ma’lumotlari</h2>
  <h3>Tarkibi / faol moddalar</h3><div>{{ medicine.active_ingredients|default:'Rasmiy ma’lumot hali kiritilmagan.'|linebreaksbr }}</div>
  <h3>Qo‘llanish holatlari</h3><div>{{ medicine.indications|default:'Rasmiy ma’lumot hali kiritilmagan.'|linebreaksbr }}</div>
  <hr><p><strong>Manba:</strong> {{ medicine.source|default:'Kiritilmagan'|linebreaksbr }}</p>
  <p><strong>Tibbiy ma’lumot tekshirilgan sana:</strong> {{ medicine.reviewed_on|date:'d.m.Y'|default:'Kiritilmagan' }}</p>
  <p class="muted">Oxirgi yangilanish: {{ medicine.updated_at|date:'d.m.Y H:i' }}</p>
</section>
<p class="notice">Qo‘llashdan oldin rasmiy yo‘riqnoma va mutaxassis tavsiyasiga amal qiling</p>
{% endblock %}
```

### `templates/catalog/edit.html`

```html
{% extends 'base.html' %}
{% block content %}
<a class="back" href="{% url 'catalog:home' %}">← Katalogga qaytish</a>
<p class="eyebrow">VAKOLATLI XODIM</p><h1>{% if medicine.pk %}Dorini tahrirlash{% else %}Dori qo‘shish{% endif %}</h1>
<p class="notice">Tarkib va qo‘llanishni faqat rasmiy yo‘riqnomadan kiriting. Manba va tekshirilgan sanani ko‘rsating.</p>
<form method="post" class="editor">{% csrf_token %}
  <section class="panel"><h2>Asosiy ma’lumotlar</h2>{{ form.as_p }}</section>
  <section class="panel"><h2>Joylashuvlar va qoldiq</h2><p class="muted">Har bir joydagi sonni alohida kiriting. Kamida bitta joylashuv kerak.</p>
    {{ placements.management_form }}{{ placements.non_form_errors }}
    <div id="placements">{% for place_form in placements %}<fieldset><legend>Joylashuv {{ forloop.counter }}</legend>{{ place_form.as_p }}</fieldset>{% endfor %}</div>
    <template id="empty-placement"><fieldset><legend>Yangi joylashuv</legend>{{ placements.empty_form.as_p }}</fieldset></template>
    <button class="button secondary" id="add-placement" type="button">+ Yana joylashuv</button>
  </section>
  <button class="button" type="submit">Saqlash</button>
</form>
{% endblock %}
```

### `templates/catalog/home.html`

```html
{% extends 'base.html' %}
{% block content %}
<section class="hero">
  <p class="eyebrow">DORILAR KATALOGI</p>
  <h1>Dorini toping.<br><span>Joyini darhol biling.</span></h1>
  <p class="muted">Savdo nomi yoki faol modda bo‘yicha tezkor qidiruv.</p>
  <form id="search-form" class="search" method="get" action="{% url 'catalog:home' %}" role="search">
    <label class="sr-only" for="query">Dori nomi yoki faol modda</label>
    <span aria-hidden="true">⌕</span>
    <input id="query" name="q" value="{{ q }}" maxlength="180" placeholder="Dori nomini yozing…" autocomplete="off" autofocus>
    <button class="button" type="submit">Qidirish</button>
  </form>
  <p class="search-hint">Nomining bir qismini yozish kifoya · Natijalar yozganingizda yangilanadi</p>
</section>
<p id="search-status" class="muted" role="status" aria-live="polite"></p>
<section id="results" aria-label="Qidiruv natijalari">{% include 'catalog/results.html' %}</section>
{% endblock %}
```

### `templates/catalog/results.html`

```html
<div class="section-heading"><h2>{% if q %}Qidiruv natijalari{% else %}Barcha dorilar{% endif %}</h2><span class="badge">{{ page_obj.paginator.count }} ta dori</span></div>
<div class="results-grid">
{% for medicine in page_obj %}
  <a class="medicine-card" href="{{ medicine.get_absolute_url }}">
    <div class="card-top"><span class="pill">{{ medicine.form }}</span>{% if medicine.is_demo %}<span class="demo">Xayoliy namuna</span>{% endif %}</div>
    <h3>{{ medicine.name }}</h3><p class="muted">{{ medicine.dosage }}</p>
    <div class="card-bottom"><strong>{{ medicine.price|floatformat:2 }} <small>so‘m</small></strong><span class="{% if medicine.total %}stock{% else %}muted{% endif %}">{{ medicine.total }} dona</span></div>
    <div class="card-link">Joylashuv va ma’lumotlar <span>↗</span></div>
  </a>
{% empty %}
  <div class="panel empty"><h3>Dori topilmadi</h3><p>Nomini tekshiring yoki faol modda bo‘yicha qidiring.</p></div>
{% endfor %}
</div>
{% if page_obj.has_other_pages %}
<nav class="pagination" aria-label="Natija sahifalari">
  {% if page_obj.has_previous %}<a href="?q={{ q|urlencode }}&amp;page={{ page_obj.previous_page_number }}">← Oldingi</a>{% endif %}
  <span>{{ page_obj.number }} / {{ page_obj.paginator.num_pages }}</span>
  {% if page_obj.has_next %}<a href="?q={{ q|urlencode }}&amp;page={{ page_obj.next_page_number }}">Keyingi →</a>{% endif %}
</nav>
{% endif %}
```

### `templates/registration/login.html`

```html
{% extends 'base.html' %}
{% block title %}Kirish · Apteka{% endblock %}
{% block content %}
<section class="panel login">
  <p class="eyebrow">XODIMLAR UCHUN</p><h1>Xush kelibsiz</h1>
  <p class="muted">Dorilar katalogiga kirish uchun hisobingizdan foydalaning.</p>
  <form method="post">{% csrf_token %}
    {{ form.as_p }}
    <input type="hidden" name="next" value="{{ next }}">
    <button class="button" type="submit">Kirish →</button>
  </form>
  <p class="muted">Hisobni apteka administratori yaratadi.</p>
</section>
{% endblock %}
```

### `static/catalog/app.css`

```css
:root{--ink:#163d36;--teal:#087f69;--muted:#687b75;--line:#dce6e0;--bg:#f5f8f5;--white:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:var(--teal);text-decoration:none}a:hover{text-decoration:underline}button,input,textarea,select{font:inherit}button,a,input,textarea{touch-action:manipulation}button{cursor:pointer}h1,h2,h3,p{margin-top:0}h1{font-size:clamp(30px,4.5vw,54px);line-height:1.14;letter-spacing:-1.8px;margin-bottom:20px}h2{font-size:22px;line-height:1.35}h3{font-size:19px;line-height:1.4}small{font-size:14px;font-weight:400}.container{width:min(1120px,calc(100% - 48px));margin:auto}.header{min-height:92px;padding:20px max(24px,calc((100% - 1120px)/2));background:white;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:20px}.brand{display:flex;align-items:center;font-size:30px;font-weight:750;letter-spacing:-1px;color:var(--ink)}.brand-dot{color:var(--teal)}.logo{display:grid;place-items:center;width:36px;height:36px;border-radius:11px;margin-right:10px;background:var(--teal);color:white;font-size:32px;line-height:1}.header nav{display:flex;flex-wrap:wrap;align-items:center;gap:22px;font-size:14px}.header form{margin:0}.username,.muted{color:var(--muted)}.text-button{border:0;background:none;color:var(--muted);padding:0}.hero{padding:64px 0 32px;max-width:850px}.hero h1 span{color:var(--teal)}.eyebrow{font-size:12px;font-weight:750;letter-spacing:2px;color:var(--teal);margin-bottom:15px}.hero>.muted{font-size:18px}.search{display:flex;align-items:center;gap:12px;background:white;border:1px solid #b4cfc4;box-shadow:0 8px 24px #173f3608;border-radius:16px;padding:10px 10px 10px 20px;margin-top:30px}.search>span{font-size:32px;color:var(--teal)}.search input{border:0;padding:10px 0;min-width:0;flex:1;background:transparent;font-size:19px}.search-hint{font-size:12px;color:var(--muted);margin:12px 0 0}.button{display:inline-block;border:1px solid var(--teal);border-radius:9px;background:var(--teal);color:white;font-weight:650;padding:12px 22px;text-align:center}.button:hover{background:#066853;color:white;text-decoration:none}.secondary{background:white;color:var(--teal)}.section-heading{display:flex;align-items:center;justify-content:space-between;margin:18px 0}.section-heading h2{margin:0}.badge,.pill{background:#e6f1ec;border-radius:6px;padding:4px 10px;color:var(--teal);font-size:12px}.results-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.medicine-card{display:block;background:white;border:1px solid var(--line);border-radius:14px;color:var(--ink);padding:22px;transition:transform .15s,border-color .15s;overflow-wrap:anywhere}.medicine-card:hover{border-color:var(--teal);transform:translateY(-3px);text-decoration:none}.card-top{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:25px;flex-wrap:wrap}.demo{color:#946214;font-size:11px}.medicine-card h3{margin-bottom:7px}.card-bottom{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:25px}.stock{font-size:13px;color:var(--teal)}.card-link{display:flex;justify-content:space-between;font-size:13px;color:var(--teal);border-top:1px solid var(--line);padding-top:15px;margin-top:20px}.panel{padding:30px;background:white;border:1px solid var(--line);border-radius:14px;margin-bottom:22px;overflow-wrap:anywhere}.empty{grid-column:1/-1;width:100%;padding:50px;text-align:center}.pagination{display:flex;gap:24px;justify-content:center;margin:32px 0}.footer{display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:12px;padding-top:30px;padding-bottom:30px;margin-top:55px;border-top:1px solid var(--line)}.back{display:inline-block;margin:30px 0}.detail-heading{display:flex;justify-content:space-between;align-items:center;gap:20px;margin:20px 0}.detail-heading h1{font-size:36px;overflow-wrap:anywhere}.detail-grid{display:grid;grid-template-columns:2fr 1fr;gap:22px}.location-panel{background:#e2f1e9;border:1px solid #bfdaca;border-radius:14px;padding:30px;margin-bottom:22px}.location{background:#ffffffa8;border-radius:10px;padding:20px;margin-top:14px}.location strong{display:block;font-size:23px;line-height:1.5;overflow-wrap:anywhere}.location span{display:block;color:var(--teal);margin-top:8px}.summary h2{font-size:28px}.total{font-size:28px}hr{border:0;border-top:1px solid var(--line);margin:24px 0}.clinical h3{margin:25px 0 8px}.notice,.demo-banner{padding:16px 20px;border:1px solid #e5d7ae;border-radius:10px;background:#fff9e9;color:#795f26;font-size:14px;margin-top:22px}.login{max-width:460px;margin:70px auto}.login h1{font-size:36px}.editor{max-width:800px}.editor label,.login label{display:block;font-weight:600;margin-bottom:7px}input:not([type=checkbox],[type=hidden]),textarea,select{width:100%;border:1px solid #bacdc2;border-radius:8px;padding:10px 12px;background:white;color:var(--ink)}input[type=checkbox]{width:20px;height:20px}.search input{border:0;background:transparent;padding-left:0}.errorlist{color:#b42318;padding-left:22px}.helptext{display:block;font-size:13px;color:var(--muted)}fieldset{border:1px solid var(--line);border-radius:10px;margin:20px 0;padding:20px}legend{color:var(--teal);font-weight:600}.sr-only{position:absolute;width:1px;height:1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #e8b95a;outline-offset:3px}
@media(max-width:800px){.results-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.detail-grid{grid-template-columns:1fr}.header{align-items:flex-start}.header nav{gap:12px}.username{display:none}.hero{padding-top:44px}}
@media(max-width:520px){.container{width:calc(100% - 32px)}.header{padding:16px;gap:12px}.brand{font-size:24px}.header nav{font-size:12px;justify-content:flex-end}.results-grid{grid-template-columns:1fr}.search{padding:8px;gap:6px}.search>span{display:none}.search input{font-size:16px}.button{padding:11px 14px}.panel,.location-panel{padding:22px}.location{padding:16px}.location strong{font-size:21px}.detail-heading{align-items:flex-start;flex-direction:column}.detail-heading h1{font-size:30px}.footer{flex-direction:column;gap:5px}.login{margin:40px auto}.hero h1{letter-spacing:-1px}.card-top{margin-bottom:18px}}
```

### `static/catalog/app.js`

```javascript
"use strict";
const searchForm = document.querySelector("#search-form");
if (searchForm) {
  const input = document.querySelector("#query");
  const results = document.querySelector("#results");
  const status = document.querySelector("#search-status");
  let timer, controller, revision = 0;
  async function search(version) {
    controller = new AbortController();
    const url = new URL(searchForm.action);
    url.searchParams.set("q", input.value.trim());
    url.searchParams.set("partial", "1");
    status.textContent = "Qidirilmoqda…";
    results.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(url, {signal: controller.signal});
      if (version !== revision) return;
      if (response.redirected) { window.location.assign(response.url); return; }
      if (!response.ok) throw new Error("Qidiruv xatosi");
      const html = await response.text();
      if (version !== revision) return;
      results.innerHTML = html;
      url.searchParams.delete("partial");
      history.replaceState(null, "", url);
      status.textContent = "Natijalar yangilandi.";
    } catch (error) {
      if (error.name !== "AbortError" && version === revision)
        status.textContent = "Qidiruv yangilanmadi. Qayta urinib ko‘ring yoki Qidirish tugmasini bosing.";
    } finally {
      if (version === revision) results.removeAttribute("aria-busy");
    }
  }
  input.addEventListener("input", () => {
    clearTimeout(timer);
    controller?.abort();
    const version = ++revision;
    timer = setTimeout(() => search(version), 220);
  });
}
const addPlacement = document.querySelector("#add-placement");
if (addPlacement) {
  addPlacement.addEventListener("click", () => {
    const total = document.querySelector("#id_places-TOTAL_FORMS");
    const index = Number(total.value);
    if (index >= 100) return;
    const html = document.querySelector("#empty-placement").innerHTML.replaceAll("__prefix__", index);
    document.querySelector("#placements").insertAdjacentHTML("beforeend", html);
    total.value = index + 1;
    if (index + 1 >= 100) addPlacement.disabled = true;
  });
}
```

### `README.md`

````markdown
# Apteka — Django dori katalogi

Python 3.10+ va Django 5.2.17. SQLite bilan bitta aptekaning ichki katalogi.
Tarkib va qo‘llanish matni avtomatik yaratilmaydi. Ularni vakolatli xodim rasmiy
yo‘riqnoma asosida kiritadi. Matn kiritilganda manba va tekshirilgan sana majburiy.
Manbaning haqiqiyligini tekshirish xodim zimmasida; sayt tashqi manbani yuklamaydi.

## Ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py setup_roles
python manage.py seed_demo
python manage.py createsuperuser
python manage.py test
python manage.py runserver
```

Windows: `source .venv/bin/activate` o‘rniga `.venv\Scripts\activate`.
Sayt: http://127.0.0.1:8000/ — administrator: http://127.0.0.1:8000/admin/.
Boshlang‘ich migratsiya loyihaga qo‘shilgan. Model o‘zgarsa:
`python manage.py makemigrations catalog`, keyin `python manage.py migrate`.

## Xodimlar

Administrator `/admin/` orqali foydalanuvchi yaratadi, keyin uning guruhini belgilaydi:

- **Aptekachi**: dori qidirish va ko‘rish.
- **Vakolatli xodim**: katalogda dori qo‘shish, tahrirlash, joylashuv, narx va qoldiqni o‘zgartirish.

Ikkala guruh uchun ham `is_active` yoqilgan bo‘lsin. `is_staff` yoki `is_superuser`
kerak emas. Administratorga kirishi zarur bo‘lgan foydalanuvchiga alohida `is_staff`
belgilanishi mumkin. Oddiy foydalanuvchiga foydalanuvchilarni yoki guruhlarni
boshqarish ruxsatini bermang. Guruhsiz foydalanuvchiga katalog yopiq.

## Ishlash tartibi

- Qidiruv savdo nomi va faol moddalar bo‘yicha, 220 ms tanaffus bilan ishlaydi.
  JavaScript o‘chirilsa ham Qidirish tugmasi ishlaydi; bir sahifada 20 ta natija.
- Har bir joylashuvda bo‘lim, polka, qator va son saqlanadi. Jami qoldiq avtomatik hisoblanadi.
- Tahrirlash sahifasida “Yana joylashuv” bilan bir nechta joy qo‘shish mumkin.
  Joyni olib tashlash uchun o‘chirish belgisini qo‘yib saqlang. Kamida bitta joy kerak.
- Xayoliy namunalarda tarkib, qo‘llanish va rasmiy manba bo‘sh. Ular banner bilan ajratilgan.
  `seed_demo` takror ishga tushirilsa, mavjud namunalar o‘zgarmaydi.
- Tibbiy ma’lumot tekshirilgan sana alohida, yozuvning oxirgi yangilanish vaqti alohida saqlanadi.
- `search_text` oddiy `save()` orqali yangilanadi. Dorilarni `bulk_create` yoki
  `QuerySet.update()` bilan o‘zgartirmang: ular model validatsiyasi va qidiruv yangilanishini chetlab o‘tadi.

## Tekshiruv va chegaralar

`python manage.py test` qidiruv, sahifalash, Unicode, joylashuvlar, narx/qoldiqni
tahrirlash, tibbiy manba validatsiyasi, rollar, CSRF va HTML escapingni tekshiradi.
Interfeys mahalliy CSS/JS bilan ishlaydi; tashqi shrift yoki CDN talab qilinmaydi.

Bu dastlabki mahalliy SQLite loyiha. Ko‘p xodim bir vaqtda faol tahrirlasa PostgreSQL
va tahrirlar to‘qnashuvini aniqlash mexanizmini qo‘shish maqsadga muvofiq.
Internetga chiqarishda `DJANGO_DEBUG=0`, tasodifiy `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`, HTTPS, WSGI server va static fayllarni xizmat qilishni sozlang;
`python manage.py collectstatic` va `python manage.py check --deploy`ni bajaring.
`runserver` mahalliy ishlab chiqish uchun.
````

## O‘rnatish va ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py setup_roles
python manage.py seed_demo
python manage.py createsuperuser
python manage.py test
python manage.py runserver
```

Sayt: http://127.0.0.1:8000/ . Administrator: http://127.0.0.1:8000/admin/ .
Administrator foydalanuvchini yaratib, **Aptekachi** yoki **Vakolatli xodim** guruhiga qo‘shadi.
Oddiy xodimga `is_staff` va `is_superuser` berish shart emas.

16 ta test muvaffaqiyatli o‘tdi. `manage.py check` xato topmadi.
Migratsiya modellarga mosligi `makemigrations --check --dry-run` orqali tekshirildi.
Xayoliy namunalarning tibbiy maydonlari bo‘sh; tibbiy ma’lumot taxmin qilinmaydi.

Django ruxsatlari uchun rasmiy manba: [Django authentication documentation](https://docs.djangoproject.com/en/5.2/topics/auth/default/).
