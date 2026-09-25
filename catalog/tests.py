from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Medicine, Placement
from .forms import PlacementForm


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", verbosity=0)
        cls.reader = User.objects.create_user("reader", password="test-password-739")
        cls.editor = User.objects.create_superuser("editor", password="test-password-739")
        cls.staff = User.objects.create_user("staff", password="test-password-739", is_staff=True)
        cls.staff.groups.add(Group.objects.get(name="Aptekachi"))
        cls.staff.user_permissions.set(Permission.objects.all())
        cls.reader.groups.add(Group.objects.get(name="Aptekachi"))
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
            "places-0-stock_snapshot": PlacementForm(instance=Placement.objects.get(pk=self.place.pk)).initial["stock_snapshot"],
            "places-1-stock_snapshot": PlacementForm(instance=self.medicine.placements.exclude(pk=self.place.pk).get()).initial["stock_snapshot"],
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
            self.assertContains(response, "10 pachka")
        self.assertContains(self.client.get("/", {"q": "topilmaydi"}), "Dori topilmadi")

    def test_all_locations_and_total_are_shown(self):
        response = self.client.get(self.medicine.get_absolute_url())
        self.assertContains(response, "Namuna bo‘limi → 3-polka → 2-qator")
        self.assertContains(response, "Zaxira → 1-polka → 1-qator")
        self.assertContains(response, "10 pachka")
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
        self.assertEqual(self.client.get("/admin/").status_code, 403)

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

    def test_staff_permissions_do_not_grant_management_access(self):
        for user in [self.reader, self.staff]:
            with self.subTest(user=user.username):
                self.client.logout()
                self.assertTrue(self.client.login(username=user.username, password="test-password-739"))
                for url in [reverse("catalog:home"), self.medicine.get_absolute_url()]:
                    response = self.client.get(url, {"q": "Alfa"})
                    self.assertContains(response, self.medicine.name)
                    for label in ["+ Dori qo‘shish", "Admin panel", "Tahrirlash"]:
                        self.assertNotContains(response, label)
                urls = [
                    reverse("catalog:create"), reverse("catalog:edit", args=[self.medicine.pk]),
                    reverse("admin:index"), reverse("admin:login"),
                    reverse("admin:catalog_medicine_changelist"),
                    reverse("admin:catalog_medicine_add"),
                    reverse("admin:catalog_medicine_change", args=[self.medicine.pk]),
                    reverse("admin:catalog_medicine_delete", args=[self.medicine.pk]),
                ]
                before = list(Medicine.objects.values())
                placements = list(Placement.objects.values())
                for url in urls:
                    with self.subTest(url=url):
                        self.assertEqual(self.client.get(url).status_code, 403)
                        self.assertEqual(self.client.post(url, self.payload()).status_code, 403)
                self.assertEqual(list(Medicine.objects.values()), before)
                self.assertEqual(list(Placement.objects.values()), placements)

    def test_superuser_management_links_and_admin_delete(self):
        self.client.logout()
        self.assertTrue(self.client.login(username="editor", password="test-password-739"))
        response = self.client.get(self.medicine.get_absolute_url())
        for label in ["+ Dori qo‘shish", "Admin panel", "Tahrirlash"]:
            self.assertContains(response, label)
        for url in [reverse("admin:index"), reverse("admin:catalog_medicine_add"),
                    reverse("admin:catalog_medicine_change", args=[self.medicine.pk])]:
            self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(reverse("admin:catalog_medicine_delete", args=[self.medicine.pk]),
                                    {"post": "yes"})
        self.assertRedirects(response, reverse("admin:catalog_medicine_changelist"))
        self.assertFalse(Medicine.objects.filter(pk=self.medicine.pk).exists())

    def test_superuser_does_not_require_staff_flag(self):
        self.editor.is_staff = False
        self.editor.save()
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("catalog:create")).status_code, 200)

    def test_group_membership_is_required_even_with_direct_permissions(self):
        user = User.objects.create_user("permissions_only")
        user.user_permissions.set(Permission.objects.all())
        self.client.force_login(user)
        for url in ["/", "/?partial=1", self.medicine.get_absolute_url()]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_login_for_both_roles_and_unauthorized_user(self):
        for user in [self.reader, self.editor]:
            self.client.logout()
            response = self.client.post(reverse("login"), {
                "username": user.username, "password": "test-password-739",
            })
            self.assertRedirects(response, "/")
        User.objects.create_user("no_role", password="test-password-739")
        self.client.logout()
        response = self.client.post(reverse("login"), {
            "username": "no_role", "password": "test-password-739",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_login_without_staff_flag(self):
        self.editor.is_staff = False
        self.editor.save(update_fields=["is_staff"])
        self.client.logout()
        response = self.client.post(reverse("admin:login"), {
            "username": self.editor.username, "password": "test-password-739",
            "next": reverse("admin:index"),
        })
        self.assertRedirects(response, reverse("admin:index"))

    def test_new_employee_gets_pharmacist_role(self):
        self.client.force_login(self.editor)
        response = self.client.post(reverse("admin:auth_user_add"), {
            "username": "new_pharmacist", "password1": "employee-password-739!",
            "password2": "employee-password-739!", "usable_password": "true",
            "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="new_pharmacist")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.groups.filter(name="Aptekachi").exists())
        self.client.logout()
        self.assertTrue(self.client.login(username=user.username, password="employee-password-739!"))
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_employee_management_is_forbidden(self):
        before = list(User.objects.values())
        for url in [reverse("admin:auth_user_add"), reverse("admin:auth_user_changelist"),
                    reverse("admin:auth_user_change", args=[self.editor.pk]),
                    reverse("admin:auth_user_delete", args=[self.editor.pk]),
                    reverse("admin:auth_group_changelist")]:
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {"post": "yes", "is_superuser": "on"}).status_code, 403)
        self.assertEqual(list(User.objects.values()), before)

    def test_setup_roles_is_idempotent(self):
        Group.objects.filter(name="Aptekachi").delete()
        call_command("setup_roles")
        group = Group.objects.get(name="Aptekachi")
        call_command("setup_roles")
        self.assertEqual(Group.objects.get(name="Aptekachi").pk, group.pk)

    def test_assign_role_preview_and_apply_preserve_password_and_other_users(self):
        target = User.objects.create_superuser("Muhammad", password="unchanged-password-739")
        before = list(User.objects.exclude(pk=target.pk).values())
        password = target.password
        call_command("assign_aptekachi", "Muhammad")
        target.refresh_from_db()
        self.assertTrue(target.is_superuser)
        self.assertFalse(target.groups.exists())
        for _ in range(2):
            call_command("assign_aptekachi", "Muhammad", apply=True)
        target.refresh_from_db()
        self.assertFalse(target.is_staff)
        self.assertFalse(target.is_superuser)
        self.assertTrue(target.groups.filter(name="Aptekachi").exists())
        self.assertEqual(target.password, password)
        self.assertEqual(list(User.objects.exclude(pk=target.pk).values()), before)
