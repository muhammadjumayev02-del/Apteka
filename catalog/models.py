from django.utils.translation import gettext_lazy
import unicodedata
import uuid
import re
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


def normalize(text):
    # SQLite uchun kirill, lotin va turli apostroflarni bir xilda qidirish.
    text = unicodedata.normalize("NFKC", text).casefold()
    mapping = dict(zip("абвгдеёзийклмнопрстуфхцчшщъыьэюяқғҳў", ["a","b","v","g","d","e","yo","z","i","y","k","l","m","n","o","p","r","s","t","u","f","x","ts","ch","sh","shch","","i","","e","yu","ya","q","g'","h","o'"]))
    text = "".join(mapping.get(c, c) for c in text)
    return " ".join(text.translate(str.maketrans({c: "'" for c in "‘’ʻʼ`"})).split())


class Medicine(models.Model):
    name = models.CharField(gettext_lazy("Savdo nomi"), max_length=180)
    dosage = models.CharField(gettext_lazy("Dozasi"), max_length=80)
    form = models.CharField(gettext_lazy("Dori shakli"), max_length=80)
    package_size = models.CharField(gettext_lazy("Qadoq hajmi"), max_length=120, blank=True)
    alternative_names = models.TextField(gettext_lazy("Muqobil nomlar"), blank=True)
    active_ingredients = models.TextField(gettext_lazy("Tarkibi / faol moddalar"), blank=True)
    indications = models.TextField(gettext_lazy("Rasmiy yo‘riqnomaga ko‘ra qo‘llanishi"), blank=True)
    source = models.TextField(gettext_lazy("Manba (yo‘riqnoma nomi, versiyasi yoki havola)"), blank=True)
    reviewed_on = models.DateField(gettext_lazy("Tibbiy ma’lumot tekshirilgan sana"), null=True, blank=True)
    price = models.DecimalField(gettext_lazy("Narxi (so‘m)"), max_digits=12, decimal_places=2,
                                validators=[MinValueValidator(0)])
    is_demo = models.BooleanField(gettext_lazy("Xayoliy namuna"), default=False)
    updated_at = models.DateTimeField(gettext_lazy("Oxirgi yangilanish"), auto_now=True)
    search_text = models.TextField(editable=False)

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = gettext_lazy("Dori")
        verbose_name_plural = gettext_lazy("Dorilar")
        constraints = [models.CheckConstraint(condition=models.Q(price__gte=0), name="price_nonnegative")]

    def __str__(self):
        return f"{self.name} · {self.dosage}"

    def get_absolute_url(self):
        return reverse("catalog:detail", args=[self.pk])

    def clean(self):
        errors = {}
        if self.active_ingredients.strip() or self.indications.strip():
            if not self.source.strip():
                errors["source"] = gettext_lazy("Tibbiy ma’lumot uchun rasmiy manbani kiriting.")
            if not self.reviewed_on:
                errors["reviewed_on"] = gettext_lazy("Tekshirilgan sanani kiriting.")
        if self.reviewed_on and self.reviewed_on > timezone.localdate():
            errors["reviewed_on"] = gettext_lazy("Sana kelajakda bo‘lishi mumkin emas.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.search_text = normalize(f"{self.name} {self.active_ingredients} {self.alternative_names}")
        self.full_clean()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"search_text", "updated_at"}
        super().save(*args, **kwargs)


class Batch(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="batches", verbose_name=gettext_lazy("Dori"))
    number = models.CharField(gettext_lazy("Partiya raqami"), max_length=120)
    expires_on = models.DateField(gettext_lazy("Yaroqlilik sanasi"), null=True, blank=True)

    class Meta:
        verbose_name = gettext_lazy("Partiya")
        verbose_name_plural = gettext_lazy("Partiyalar")
        constraints = [models.UniqueConstraint(fields=["medicine", "number"], name="unique_batch")]

    def __str__(self):
        return f"{self.medicine} / {self.number}"


class Placement(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="placements", verbose_name=gettext_lazy("Dori"))
    batch = models.ForeignKey(Batch, on_delete=models.RESTRICT, related_name="placements", blank=True, verbose_name=gettext_lazy("Partiya"))
    department = models.CharField(gettext_lazy("Bo‘lim"), max_length=120)
    shelf = models.PositiveSmallIntegerField(gettext_lazy("Polka"), validators=[MinValueValidator(1)])
    row = models.PositiveSmallIntegerField(gettext_lazy("Qator"), validators=[MinValueValidator(1)])
    quantity = models.PositiveIntegerField(gettext_lazy("Mavjud soni"), default=0)

    class Meta:
        ordering = ["department", "shelf", "row"]
        verbose_name = gettext_lazy("Joylashuv")
        verbose_name_plural = gettext_lazy("Joylashuvlar")
        constraints = [
            models.UniqueConstraint(fields=["medicine", "batch", "department", "shelf", "row"], name="unique_placement"),
            models.CheckConstraint(condition=models.Q(shelf__gte=1, row__gte=1), name="positive_coordinates"),
        ]

    @property
    def location_key(self):
        # Stable identifier used by signed sale snapshots and stored history.
        return f"{self.department} → {self.shelf}-polka → {self.row}-qator"

    def __str__(self):
        return gettext_lazy("%(department)s → %(shelf)s-polka → %(row)s-qator") % {
            "department": self.department, "shelf": self.shelf, "row": self.row,
        }

    def clean(self):
        if self.batch_id and self.batch.medicine_id != self.medicine_id:
            raise ValidationError({"batch": gettext_lazy("Partiya shu doriga tegishli bo‘lishi kerak.")})

    def save(self, *args, **kwargs):
        if not self.batch_id:
            self.batch, _ = Batch.objects.get_or_create(medicine_id=self.medicine_id, number="Boshlang‘ich partiya")
        self.clean()
        super().save(*args, **kwargs)


class ShiftSchedule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="shift_schedules", verbose_name=gettext_lazy("Aptekachi"))
    planned_start = models.DateTimeField(gettext_lazy("Rejalashtirilgan boshlanish"))
    planned_end = models.DateTimeField(gettext_lazy("Rejalashtirilgan tugash"))

    class Meta:
        ordering = ["-planned_start", "-pk"]
        constraints = [models.CheckConstraint(condition=models.Q(planned_end__gt=models.F("planned_start")), name="schedule_positive_duration")]
        verbose_name = gettext_lazy("Ish jadvali")
        verbose_name_plural = gettext_lazy("Ish jadvallari")

    def clean(self):
        if self.planned_start and self.planned_end:
            if self.planned_end <= self.planned_start:
                raise ValidationError(gettext_lazy("Tugash vaqti boshlanishdan keyin bo‘lishi kerak."))
            if self.user_id and ShiftSchedule.objects.filter(user_id=self.user_id, planned_start__lt=self.planned_end, planned_end__gt=self.planned_start).exclude(pk=self.pk).exists():
                raise ValidationError(gettext_lazy("Bu xodimning shu vaqtda boshqa smenasi bor."))

    def __str__(self):
        return f"{self.user} · {timezone.localtime(self.planned_start):%d.%m.%Y %H:%M}"


class Shift(models.Model):
    schedule = models.OneToOneField(ShiftSchedule, null=True, blank=True, on_delete=models.PROTECT, related_name="shift", verbose_name=gettext_lazy("Ish jadvali"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="shifts", verbose_name=gettext_lazy("Xodim"))
    started_at = models.DateTimeField(default=timezone.now, verbose_name=gettext_lazy("Boshlangan vaqt"))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=gettext_lazy("Yakunlangan vaqt"))

    def __str__(self):
        return gettext_lazy("Smena #%(id)s · %(name)s") % {"id": self.pk, "name": self.user}

    class Meta:
        verbose_name = gettext_lazy("Smena")
        verbose_name_plural = gettext_lazy("Smenalar")
        constraints = [models.UniqueConstraint(fields=["user"], condition=models.Q(ended_at__isnull=True), name="one_open_shift")]
        ordering = ["-started_at", "-pk"]

    @property
    def worked_time(self):
        minutes = int(((self.ended_at or timezone.now()) - self.started_at).total_seconds() // 60)
        return gettext_lazy("%(hours)s soat %(minutes)s daqiqa") % {"hours": minutes // 60, "minutes": minutes % 60}


class Sale(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="sales", verbose_name=gettext_lazy("Smena"))
    placement = models.ForeignKey(Placement, on_delete=models.PROTECT, verbose_name=gettext_lazy("Partiya va joylashuv"))
    name = models.CharField(max_length=180, verbose_name=gettext_lazy("Dori nomi"))
    dosage = models.CharField(max_length=80, verbose_name=gettext_lazy("Dozasi"))
    form = models.CharField(max_length=80, verbose_name=gettext_lazy("Dori shakli"))
    package_size = models.CharField(max_length=120, verbose_name=gettext_lazy("Qadoq hajmi"))
    quantity = models.PositiveIntegerField(verbose_name=gettext_lazy("Pachkalar soni"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=gettext_lazy("Bir pachka narxi"))
    total = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=gettext_lazy("Jami narx"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=gettext_lazy("Sana va vaqt"))
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name=gettext_lazy("Bekor qilingan vaqt"))
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, verbose_name=gettext_lazy("Bekor qilgan xodim"))

    def __str__(self):
        return gettext_lazy("Sotuv #%(id)s · %(name)s") % {"id": self.pk, "name": self.name}

    class Meta:
        verbose_name = gettext_lazy("Sotuv")
        verbose_name_plural = gettext_lazy("Sotuvlar")
        ordering = ["-created_at", "-pk"]
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0, total__gte=0, unit_price__gte=0), name="valid_sale")]


class StockTransfer(models.Model):
    source = models.ForeignKey(Placement, on_delete=models.PROTECT, related_name="outgoing_transfers", verbose_name=gettext_lazy("Oldingi joy"))
    destination = models.ForeignKey(Placement, on_delete=models.PROTECT, related_name="incoming_transfers", verbose_name=gettext_lazy("Yangi joy"))
    source_label = models.CharField(max_length=200, verbose_name=gettext_lazy("Oldingi joy"))
    destination_label = models.CharField(max_length=200, verbose_name=gettext_lazy("Yangi joy"))
    quantity = models.PositiveIntegerField(verbose_name=gettext_lazy("Pachkalar soni"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name=gettext_lazy("Xodim"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=gettext_lazy("Sana va vaqt"))

    @staticmethod
    def localized_location(label):
        match = re.fullmatch(r'(.*) → (\d+)-polka → (\d+)-qator', label)
        if not match:
            return label
        return gettext_lazy("%(department)s → %(shelf)s-polka → %(row)s-qator") % {
            'department': match[1], 'shelf': match[2], 'row': match[3],
        }

    @property
    def source_display(self):
        return self.localized_location(self.source_label)

    @property
    def destination_display(self):
        return self.localized_location(self.destination_label)

    def __str__(self):
        return gettext_lazy("Ko‘chirish #%(id)s · %(name)s") % {"id": self.pk, "name": self.user}

    class Meta:
        verbose_name = gettext_lazy("Polkalar orasida ko‘chirish")
        verbose_name_plural = gettext_lazy("Polkalar orasida ko‘chirishlar")
        ordering = ["-created_at", "-pk"]
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name="positive_transfer")]
