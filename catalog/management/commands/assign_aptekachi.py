from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from catalog.roles import APTEKACHI_GROUP


class Command(BaseCommand):
    help = "Bitta hisobni Aptekachi roliga o‘tkazadi. Yozish uchun --apply kerak."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--apply", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.select_for_update().get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError("Bunday foydalanuvchi mavjud emas.")
        self.stdout.write(f"{user.username}: Aptekachi guruhiga qo‘shiladi; is_staff=False, is_superuser=False. Parol o‘zgarmaydi.")
        if not options["apply"]:
            self.stdout.write("Faqat ko‘rish. Saqlash uchun --apply ishlating.")
            return
        group, _ = Group.objects.get_or_create(name=APTEKACHI_GROUP)
        user.groups.add(group)
        user.is_staff = False
        user.is_superuser = False
        user.save(update_fields=["is_staff", "is_superuser"])
        self.stdout.write(self.style.SUCCESS("Rol saqlandi."))
