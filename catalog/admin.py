from django.utils.translation import gettext_lazy
from functools import wraps

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from .models import Medicine, Placement, Batch, Shift, Sale, StockTransfer
from .forms import SuperuserAuthenticationForm, PlacementForm, PlacementSet
from .roles import APTEKACHI_GROUP
from .dashboard import dashboard_context
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator


class SuperuserAdminSite(admin.AdminSite):
    login_form = SuperuserAuthenticationForm
    index_template = "admin/pharmacy_index.html"

    def each_context(self, request):
        context = super().each_context(request)
        url_name = request.resolver_match.url_name if request.resolver_match else None
        sections = {
            f'{model}_{action}': section
            for model, section in (
                ('catalog_medicine', 'medicines'),
                ('catalog_batch', 'batches'),
                ('auth_user', 'users'),
                ('catalog_shift', 'shifts'),
                ('catalog_sale', 'sales'),
                ('catalog_stocktransfer', 'transfers'),
                ('catalog_stockreceipt', 'receipts'),
                ('catalog_placement', 'locations'),
            )
            for action in ('changelist', 'add', 'change', 'history', 'delete')
        }
        sections.update({
            'catalog_medicine_add': 'medicine_add',
            'catalog_batch_add': 'batch_add',
            'auth_user_password_change': 'users',
        })
        context['active_section'] = sections.get(url_name)
        return context

    @method_decorator(require_GET)
    def index(self, request, extra_context=None):
        return super().index(request, {**dashboard_context(), **(extra_context or {})})

    def has_permission(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            raise PermissionDenied
        return request.user.is_active and request.user.is_superuser

    def get_urls(self):
        # Include login and auxiliary admin URLs in the same access policy.
        def guard(view):
            @wraps(view)
            def wrapped(request, *args, **kwargs):
                if request.user.is_authenticated and not self.has_permission(request):
                    raise PermissionDenied
                return view(request, *args, **kwargs)
            return wrapped

        urls = super().get_urls()
        for pattern in urls:
            if hasattr(pattern, "callback"):
                pattern.callback = guard(pattern.callback)
        return urls


site = SuperuserAdminSite(name="admin")
class LocalizedPermissionsMixin:
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name in {"permissions", "user_permissions"}:
            field.queryset = field.queryset.select_related("content_type")
            field.label_from_instance = self.permission_label
        return field

    @staticmethod
    def permission_label(permission):
        model = permission.content_type.model_class()
        if model is None:
            return permission.name
        actions = {
            "add": gettext_lazy("Qo‘shish: %(model)s"),
            "change": gettext_lazy("O‘zgartirish: %(model)s"),
            "delete": gettext_lazy("O‘chirish: %(model)s"),
            "view": gettext_lazy("Ko‘rish: %(model)s"),
        }
        for action, label in actions.items():
            if permission.codename == f"{action}_{model._meta.model_name}":
                return label % {"model": model._meta.verbose_name}
        # Custom permission names are user data, not built-in interface labels.
        return permission.name


class PharmacyGroupAdmin(LocalizedPermissionsMixin, GroupAdmin):
    pass


class PharmacyUserAdmin(LocalizedPermissionsMixin, UserAdmin):
    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_staff = False
            obj.is_superuser = False
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if not change:
            group, _ = Group.objects.get_or_create(name=APTEKACHI_GROUP)
            form.instance.groups.add(group)


site.register(User, PharmacyUserAdmin)
site.register(Group, PharmacyGroupAdmin)


class PlacementInline(admin.TabularInline):
    model = Placement
    form = PlacementForm
    formset = PlacementSet
    extra = 1
    min_num = 1
    validate_min = True


@admin.register(Medicine, site=site)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ["name", "dosage", "form", "price", "stock", "is_demo", "updated_at"]
    search_fields = ["name", "active_ingredients", "alternative_names"]
    list_filter = ["is_demo", "form"]
    readonly_fields = ["updated_at"]
    inlines = [PlacementInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.method == 'POST' and request.resolver_match.url_name == 'catalog_medicine_change':
            # Lock before reading inline stock, in the same order as sales.
            return queryset.select_for_update()
        return queryset.annotate(stock_total=Sum('placements__quantity', default=0))

    @admin.display(description=gettext_lazy('Qoldiq (pachka)'), ordering='stock_total')
    def stock(self, obj):
        return obj.stock_total


site.site_header = gettext_lazy("Apteka boshqaruvi")
site.site_title = "Apteka"
site.index_title = gettext_lazy("Boshqaruv paneli")


@admin.register(Batch, site=site)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['medicine', 'number', 'received_on', 'expires_on', 'received_quantity', 'remaining_quantity']
    search_fields = ['medicine__name', 'number']

    @admin.display(description=gettext_lazy('Kirim soni'))
    def received_quantity(self, obj):
        opening = obj.placements.aggregate(n=Sum('opening_quantity', default=0))['n']
        receipts = StockReceipt.objects.filter(placement__batch=obj).aggregate(n=Sum('quantity', default=0))['n']
        return opening + receipts

    @admin.display(description=gettext_lazy('Mavjud soni'))
    def remaining_quantity(self, obj):
        return obj.placements.aggregate(n=Sum('quantity', default=0))['n']

    def get_readonly_fields(self, request, obj=None):
        return ['medicine', 'number'] if obj else []


class HistoryAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Shift, site=site)
class ShiftAdmin(HistoryAdmin):
    list_display = ['user', 'started_at', 'ended_at']


@admin.register(Sale, site=site)
class SaleAdmin(HistoryAdmin):
    list_display = ['name', 'shift', 'quantity', 'total', 'payment_method', 'created_at', 'cancelled_at']
    list_filter = ['payment_method', 'created_at', 'cancelled_at', 'shift__user', 'shift']
    search_fields = ['name', 'shift__user__username']
    date_hierarchy = 'created_at'
    list_select_related = ['shift']


@admin.register(StockTransfer, site=site)
class TransferAdmin(HistoryAdmin):
    list_display = ['user', 'source_display', 'destination_display', 'quantity', 'created_at']
    exclude = ['source_label', 'destination_label']
    readonly_fields = ['source_display', 'destination_display']

    @admin.display(description=gettext_lazy('Oldingi joy'))
    def source_display(self, obj):
        return obj.source_display

    @admin.display(description=gettext_lazy('Yangi joy'))
    def destination_display(self, obj):
        return obj.destination_display


from .models import StockReceipt
from .services import receive_stock


@admin.register(StockReceipt, site=site)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['placement', 'quantity', 'received_on', 'user']
    fields = ['placement', 'quantity', 'received_on']

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        saved = receive_stock(request.user, obj.placement, obj.quantity, obj.received_on)
        obj.pk = saved.pk
        obj.user = request.user


@admin.register(Placement, site=site)
class LocationAdmin(HistoryAdmin):
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    list_display = ['medicine', 'batch', 'department', 'shelf', 'row', 'quantity']
    search_fields = ['medicine__name', 'department', 'batch__number']
