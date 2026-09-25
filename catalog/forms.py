from django.utils.translation import gettext_lazy
from django import forms
from django.core import signing
from django.contrib.auth.forms import AuthenticationForm
from django.forms import inlineformset_factory
from .models import Medicine, Placement, Batch
from .roles import can_view_catalog


class UzbekAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label=gettext_lazy("Foydalanuvchi nomi"), widget=forms.TextInput(attrs={"autofocus": True}))
    password = forms.CharField(label=gettext_lazy("Parol"), strip=False, widget=forms.PasswordInput)
    error_messages = {
        "invalid_login": gettext_lazy("Foydalanuvchi nomi yoki parol noto‘g‘ri."),
        "inactive": gettext_lazy("Bu hisob faol emas."),
    }


    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not can_view_catalog(user):
            raise forms.ValidationError(gettext_lazy("Bu hisobga katalogga kirish ruxsati berilmagan."), code="no_role")


class SuperuserAuthenticationForm(UzbekAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise forms.ValidationError(gettext_lazy("Boshqaruv faqat administrator uchun."), code="not_superuser")


class SimpleFormMixin:
    required_css_class = 'required'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.error_messages.update(required=gettext_lazy('Bu maydonni to‘ldiring.'), invalid=gettext_lazy('To‘g‘ri qiymat kiriting.'), invalid_choice=gettext_lazy('Ro‘yxatdan tanlang.'), min_value=gettext_lazy('Kamida %(limit_value)s kiriting.'), max_value=gettext_lazy('Ko‘pi bilan %(limit_value)s kiriting.'))


class MedicineForm(SimpleFormMixin, forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ["name", "dosage", "form", "package_size", "price", "alternative_names", "active_ingredients", "indications",
                  "source", "reviewed_on", "is_demo"]
        widgets = {
            "reviewed_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            **{field: forms.Textarea(attrs={"rows": 3})
               for field in ["active_ingredients", "indications", "source"]},
        }


class PlacementForm(SimpleFormMixin, forms.ModelForm):
    stock_snapshot = forms.CharField(widget=forms.HiddenInput, required=False)

    @staticmethod
    def snapshot(instance):
        return [instance.pk, instance.batch_id, instance.department,
                instance.shelf, instance.row, instance.quantity]

    def clean(self):
        data = super().clean()
        if self.instance.pk:
            try:
                saved = signing.loads(data.get('stock_snapshot', ''), salt='placement-edit')
            except signing.BadSignature:
                saved = None
            if saved != self.snapshot(self.instance):
                raise forms.ValidationError(gettext_lazy('Qoldiq yoki joylashuv o‘zgargan. Sahifani yangilab, qaytadan kiriting.'))
        return data

    class Meta:
        model = Placement
        fields = ['batch', 'department', 'shelf', 'row', 'quantity']

    def clean_batch(self):
        return self.cleaned_data.get('batch') or (self.instance.batch if self.instance.pk else None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['stock_snapshot'] = signing.dumps(self.snapshot(self.instance), salt='placement-edit')
        self.fields['batch'].queryset = Batch.objects.filter(medicine_id=self.instance.medicine_id)
        self.fields['batch'].label = gettext_lazy('Partiya (bo‘sh bo‘lsa boshlang‘ich partiya)')


class PlacementSet(forms.BaseInlineFormSet):
    def get_queryset(self):
        queryset = super().get_queryset()
        # Both editing views validate and save inside an atomic transaction.
        return queryset.select_for_update() if self.is_bound else queryset

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        seen = set()
        for form in self.forms:
            data = form.cleaned_data
            if not data:
                continue
            instance = form.instance
            used = instance.pk and (instance.sale_set.exists() or instance.outgoing_transfers.exists() or instance.incoming_transfers.exists())
            if used and (data.get('DELETE') or any(k in form.changed_data for k in ('batch', 'department', 'shelf', 'row'))):
                raise forms.ValidationError(gettext_lazy('Tarixga bog‘langan joyni o‘chirish yoki almashtirish mumkin emas. Ko‘chirish sahifasidan foydalaning.'))
            if data.get('DELETE'):
                continue
            batch = data.get('batch')
            key = (batch.number if batch else 'Boshlang‘ich partiya', data.get('department'), data.get('shelf'), data.get('row'))
            if key in seen:
                raise forms.ValidationError(gettext_lazy('Bir partiya uchun joylashuv takrorlangan.'))
            seen.add(key)


PlacementFormSet = inlineformset_factory(
    Medicine, Placement, form=PlacementForm, formset=PlacementSet,
    extra=1, can_delete=True, min_num=1, validate_min=True,
    max_num=100, validate_max=True,
)


class SaleForm(SimpleFormMixin, forms.Form):
    placement = forms.ModelChoiceField(label=gettext_lazy("Partiya va joylashuv"), queryset=Placement.objects.none())
    quantity = forms.IntegerField(label=gettext_lazy("Sotiladigan pachkalar soni"), min_value=1, max_value=1000000)

    def __init__(self, *args, medicine, **kwargs):
        super().__init__(*args, **kwargs)
        self.medicine = medicine
        self.fields['placement'].queryset = medicine.placements.filter(quantity__gt=0).select_related('batch')
        self.fields['placement'].label_from_instance = lambda p: gettext_lazy('%(batch)s · %(place)s · %(quantity)s pachka') % {'batch': p.batch.number, 'place': p, 'quantity': p.quantity}

    def clean(self):
        data = super().clean()
        if not self.medicine.package_size.strip():
            raise forms.ValidationError(gettext_lazy('Sotuvdan oldin admin qadoq hajmini kiritishi kerak.'))
        placement = data.get('placement')
        if placement:
            if data.get('quantity', 0) > placement.quantity:
                self.add_error('quantity', gettext_lazy('Bu joyda faqat %(quantity)s pachka bor. Kamroq son kiriting.') % {'quantity': placement.quantity})
            from .services import validate_expiry
            try:
                validate_expiry(placement.batch)
            except forms.ValidationError as error:
                self.add_error('placement', error)
        return data


class TransferForm(SimpleFormMixin, forms.Form):
    source = forms.ModelChoiceField(label=gettext_lazy("Manba partiya va joy"), queryset=Placement.objects.none())
    department = forms.CharField(label=gettext_lazy("Yangi bo‘lim"), max_length=120)
    shelf = forms.IntegerField(label=gettext_lazy("Yangi polka"), min_value=1, max_value=32767)
    row = forms.IntegerField(label=gettext_lazy("Yangi qator"), min_value=1, max_value=32767)
    quantity = forms.IntegerField(label=gettext_lazy("Pachkalar soni"), min_value=1, max_value=1000000)

    def __init__(self, *args, medicine, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['source'].queryset = medicine.placements.filter(quantity__gt=0).select_related('batch')
        self.fields['source'].label_from_instance = lambda p: gettext_lazy('%(batch)s · %(place)s · %(quantity)s pachka') % {'batch': p.batch.number, 'place': p, 'quantity': p.quantity}


    def clean(self):
        data = super().clean()
        source = data.get('source')
        if source and data.get('quantity', 0) > source.quantity:
            self.add_error('quantity', gettext_lazy('Bu joyda qoldiq yetarli emas: faqat %(quantity)s pachka bor. Kamroq son kiriting.') % {'quantity': source.quantity})
        return data


class ShiftScheduleForm(SimpleFormMixin, forms.ModelForm):
    class Meta:
        from .models import ShiftSchedule
        model = ShiftSchedule
        fields = ['user', 'planned_start', 'planned_end']
        widgets = {field: forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'})
                   for field in ('planned_start', 'planned_end')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        from .roles import APTEKACHI_GROUP
        self.fields['user'].queryset = get_user_model().objects.filter(is_active=True, groups__name=APTEKACHI_GROUP).distinct()
