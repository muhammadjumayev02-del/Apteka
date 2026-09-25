from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from catalog.roles import APTEKACHI_GROUP


class Command(BaseCommand):
    help = "Aptekachi guruhini xavfsiz yaratadi; mavjud hisoblarni o‘zgartirmaydi."

    def handle(self, *args, **options):
        Group.objects.get_or_create(name=APTEKACHI_GROUP)
        self.stdout.write(self.style.SUCCESS("Aptekachi guruhi tayyor."))
