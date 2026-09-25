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
