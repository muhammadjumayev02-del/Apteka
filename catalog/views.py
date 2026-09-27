from django.utils.translation import gettext_lazy
import uuid
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.utils import timezone
from .models import Shift, Sale, StockTransfer, ShiftSchedule
from .forms import SaleForm, TransferForm, ShiftScheduleForm
from .services import snapshot, confirm_sale, transfer_stock, cancel_sale
from .search import search
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from .forms import MedicineForm, PlacementFormSet
from .models import Medicine
from .permissions import catalog_access_required, superuser_required


def medicines():
    return Medicine.objects.prefetch_related("placements__batch").annotate(total=Sum("placements__quantity", default=0)).order_by("name", "pk")


@login_required
@catalog_access_required
@require_GET
def home(request):
    query = request.GET.get("q", "").strip()[:180]
    items = medicines()
    items, suggested = search(items, query)
    page = Paginator(items, 20).get_page(request.GET.get("page"))
    template = "catalog/results.html" if request.GET.get("partial") == "1" else "catalog/home.html"
    return render(request, template, {"page_obj": page, "q": query, "suggested": suggested})


@login_required
@catalog_access_required
@require_GET
def detail(request, pk):
    medicine = get_object_or_404(medicines().prefetch_related("placements"), pk=pk)
    return render(request, "catalog/detail.html", {"medicine": medicine})


@login_required
@superuser_required
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
                messages.success(request, gettext_lazy("Dori ma’lumotlari saqlandi."))
                return redirect(medicine)
    return render(request, "catalog/edit.html", {"form": form, "placements": placements, "medicine": medicine})


@login_required
@catalog_access_required
@require_GET
def locations(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    return render(request, 'catalog/locations.html', {'medicine': medicine,
                  'places': medicine.placements.filter(quantity__gt=0).select_related('batch')})


@login_required
@catalog_access_required
@require_http_methods(['GET', 'POST'])
def sell(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    form = SaleForm(request.POST if request.method == 'POST' else None, medicine=medicine)
    shift = Shift.objects.filter(user=request.user, ended_at__isnull=True).first()
    if request.method == 'POST':
        if not shift:
            form.add_error(None, gettext_lazy('Sotuv uchun smenani admin ochishi kerak.'))
        elif form.is_valid():
            data = {'medicine': medicine.pk, 'placement': form.cleaned_data['placement'].pk,
                    'location': form.cleaned_data['placement'].location_key, 'batch': form.cleaned_data['placement'].batch_id,
                    'payment_method': form.cleaned_data['payment_method'],
                    'quantity': form.cleaned_data['quantity'], 'price': str(medicine.price),
                    'product': snapshot(medicine), 'user': request.user.pk, 'shift': shift.pk,
                    'token': str(uuid.uuid4()), 'is_demo': medicine.is_demo}
            if request.POST.get('action') == 'cart':
                cart = request.session.get('cart', [])
                if len(cart) < 100:
                    cart.append(data)
                    request.session['cart'] = cart
                return redirect('catalog:cart')
            return render(request, 'catalog/confirm_sale.html', {'medicine': medicine, 'data': data,
                          'total': medicine.price * data['quantity'], 'token': signing.dumps(data, salt='sale'),
                          'payment_label': Sale.PaymentMethod(data['payment_method']).label,
                          'place': form.cleaned_data['placement']})
    return render(request, 'catalog/sell.html', {'medicine': medicine, 'form': form, 'open_shift': shift})


@login_required
@catalog_access_required
@require_http_methods(['POST'])
def sale_confirm(request):
    try:
        data = signing.loads(request.POST.get('token', ''), salt='sale', max_age=900)
        if data['user'] != request.user.pk:
            raise PermissionDenied
        sale = confirm_sale(request.user, data)
    except (signing.BadSignature, ValidationError, Medicine.DoesNotExist) as error:
        messages.error(request, ' '.join(error.messages) if isinstance(error, ValidationError) else gettext_lazy('Tasdiqlash muddati tugagan yoki ma’lumot o‘zgargan. Sotuvni qaytadan tayyorlang.'))
        return redirect('catalog:home')
    messages.success(request, gettext_lazy('Sotuv tasdiqlandi.'))
    return redirect('catalog:shift_detail', pk=sale.shift_id)


@login_required
@catalog_access_required
@require_http_methods(['GET', 'POST'])
def shifts(request):
    if request.method == 'POST':
        if not request.user.is_superuser:
            raise PermissionDenied
        if request.POST.get('action') == 'start':
            try:
                with transaction.atomic():
                    schedule = None
                    if request.POST.get('schedule'):
                        if not request.POST['schedule'].isdecimal():
                            messages.error(request, gettext_lazy('Smena noto‘g‘ri tanlangan.'))
                            return redirect('catalog:shifts')
                        schedule = get_object_or_404(ShiftSchedule.objects.select_for_update(), pk=request.POST['schedule'])
                        if Shift.objects.filter(schedule=schedule).exists():
                            messages.error(request, gettext_lazy('Bu smena allaqachon boshlangan yoki yakunlangan.'))
                            return redirect('catalog:shifts')
                    Shift.objects.get_or_create(user=schedule.user if schedule else request.user, ended_at__isnull=True, defaults={'schedule': schedule})
            except IntegrityError:
                pass  # The database enforces one open shift during simultaneous starts.
            messages.success(request, gettext_lazy('Smena boshlandi. Sotuv qilish mumkin.'))
        elif request.POST.get('action') == 'end':
            Shift.objects.filter(pk=request.POST.get('shift'), ended_at__isnull=True).update(ended_at=timezone.now())
            messages.success(request, gettext_lazy('Smena yakunlandi.'))
        return redirect('catalog:shifts')
    valid_sales = Q(sales__cancelled_at__isnull=True)
    items = Shift.objects.select_related('user', 'schedule').annotate(
        sale_count=Count('sales', filter=valid_sales),
        packages=Sum('sales__quantity', filter=valid_sales, default=0),
        revenue=Sum('sales__total', filter=valid_sales, default=0))
    schedules = ShiftSchedule.objects.select_related('user').filter(shift__isnull=True)
    if not request.user.is_superuser:
        items = items.filter(user=request.user)
        schedules = schedules.filter(user=request.user)
    return render(request, 'catalog/shifts.html', {'shifts': items, 'schedules': schedules,
                  'open_shift': Shift.objects.filter(user=request.user, ended_at__isnull=True).first()})


@login_required
@superuser_required
@require_http_methods(['GET', 'POST'])
def schedule_create(request):
    form = ShiftScheduleForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        with transaction.atomic():
            # Serialize schedule creation for the selected employee on databases with row locks.
            from django.contrib.auth import get_user_model
            user_id = request.POST.get('user', '')
            if user_id.isdecimal():
                get_user_model().objects.select_for_update().filter(pk=user_id).first()
            if form.is_valid():
                form.save()
                messages.success(request, gettext_lazy('Ish jadvali saqlandi.'))
                return redirect('catalog:shifts')
    return render(request, 'catalog/schedule_form.html', {'form': form})


@login_required
@catalog_access_required
@require_GET
def shift_detail(request, pk):
    items = Shift.objects.all()
    if not request.user.is_superuser:
        items = items.filter(user=request.user)
    shift = get_object_or_404(items, pk=pk)
    return render(request, 'catalog/shift_detail.html', {'shift': shift, 'sales': shift.sales.all(),
                  'totals': shift.sales.filter(cancelled_at__isnull=True).aggregate(quantity=Sum('quantity', default=0), total=Sum('total', default=0))})


@login_required
@catalog_access_required
@require_http_methods(['GET', 'POST'])
def sale_cancel(request, pk):
    sales = Sale.objects.all()
    if not request.user.is_superuser:
        sales = sales.filter(shift__user=request.user)
    sale = get_object_or_404(sales, pk=pk)
    if request.method == 'GET':
        return render(request, 'catalog/cancel_sale.html', {'sale': sale, 'lines': Sale.objects.filter(order_token=sale.order_token) if sale.order_token else [sale]})
    if cancel_sale(sale, request.user):
        messages.success(request, gettext_lazy('Sotuv bekor qilindi. Pachkalar qoldiqqa qaytarildi.'))
    else:
        messages.error(request, gettext_lazy('Bu sotuv allaqachon bekor qilingan.'))
    return redirect('catalog:shift_detail', pk=sale.shift_id)


@login_required
@superuser_required
@require_http_methods(['GET', 'POST'])
def transfer(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    form = TransferForm(request.POST if request.method == 'POST' else None, medicine=medicine)
    if request.method == 'POST' and form.is_valid():
        try:
            transfer_stock(request.user, medicine, form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, gettext_lazy('Pachkalar ko‘chirildi. Umumiy qoldiq o‘zgarmadi.'))
            return redirect('catalog:transfer', pk=pk)
    return render(request, 'catalog/transfer.html', {'medicine': medicine, 'form': form,
                  'history': StockTransfer.objects.filter(source__medicine=medicine).select_related('user', 'source__batch')})


@login_required
@catalog_access_required
@require_http_methods(['GET', 'POST'])
def cart(request):
    from decimal import Decimal
    from .services import confirm_cart
    lines = request.session.get('cart', [])
    if 'cart_token' not in request.session:
        request.session['cart_token'] = str(uuid.uuid4())
    if request.method == 'POST':
        if request.POST.get('action') == 'clear':
            request.session['cart'] = []
            request.session.pop('cart_token', None)
            return redirect('catalog:cart')
        try:
            confirm_cart(request.user, lines, request.session['cart_token'])
        except (ValidationError, Medicine.DoesNotExist) as error:
            messages.error(request, ' '.join(error.messages) if isinstance(error, ValidationError) else gettext_lazy('Ro‘yxatdan tanlang.'))
        else:
            request.session['cart'] = []
            request.session.pop('cart_token', None)
            messages.success(request, gettext_lazy('Sotuv tasdiqlandi.'))
            return redirect('catalog:shifts')
    display_lines = [{**line, 'payment_label': dict(Sale.PaymentMethod.choices).get(line.get('payment_method'), Sale.PaymentMethod.UNKNOWN.label), 'location_display': StockTransfer.localized_location(line['location'])} for line in lines]
    return render(request, 'catalog/cart.html', {'lines': display_lines, 'total': sum(Decimal(x['price']) * x['quantity'] for x in lines)})


@login_required
@superuser_required
@require_GET
def reports(request):
    from django import forms
    from django.http import HttpResponse
    import csv
    from .forms import SimpleFormMixin
    from django.contrib.auth import get_user_model
    class ReportForm(SimpleFormMixin, forms.Form):
        start = forms.DateField(label=gettext_lazy('Boshlanish sanasi'), initial=timezone.localdate, widget=forms.DateInput(attrs={'type': 'date'}))
        end = forms.DateField(label=gettext_lazy('Tugash sanasi'), initial=timezone.localdate, widget=forms.DateInput(attrs={'type': 'date'}))
        employee = forms.ModelChoiceField(label=gettext_lazy('Xodim'), queryset=get_user_model().objects.order_by('username'), required=False)
        shift = forms.ModelChoiceField(label=gettext_lazy('Smena'), queryset=Shift.objects.select_related('user'), required=False)
    form = ReportForm(request.GET or None)
    sales = Sale.objects.filter(cancelled_at__isnull=True)
    if request.GET:
        if form.is_valid() and form.cleaned_data['start'] <= form.cleaned_data['end']:
            sales = sales.filter(created_at__date__range=(form.cleaned_data['start'], form.cleaned_data['end']))
            if form.cleaned_data['employee']:
                sales = sales.filter(shift__user=form.cleaned_data['employee'])
            if form.cleaned_data['shift']:
                sales = sales.filter(shift=form.cleaned_data['shift'])
        else:
            sales = sales.none()
            form.add_error(None, gettext_lazy('To‘g‘ri qiymat kiriting.'))
    else:
        sales = sales.filter(created_at__date=timezone.localdate())
    if request.GET.get('export') == 'csv' and form.is_valid():
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="sales.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow([str(gettext_lazy(x)) for x in ['Sana va vaqt', 'Xodim', 'Dori', 'Pachkalar soni', 'Jami narx', 'To‘lov usuli', 'Naqd pul tushumi', 'Chek raqami', 'Smena']])
        for sale in sales.select_related('shift__user'):
            def safe(value):
                value = str(value)
                return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value
            writer.writerow([safe(x) for x in [sale.created_at, sale.shift.user, sale.name, sale.quantity, sale.total, sale.get_payment_method_display(), sale.total if sale.payment_method == Sale.PaymentMethod.CASH else 0, sale.order_token or sale.token, sale.shift_id]])
        return response
    cash = sales.filter(payment_method=Sale.PaymentMethod.CASH)
    # Each cart receipt counts once; a standalone sale uses its unique token.
    from django.db.models.functions import Coalesce
    cash_totals = cash.aggregate(revenue=Sum('total', default=0),
                                count=Count(Coalesce('order_token', 'token'), distinct=True))
    unknown_totals = sales.filter(payment_method=Sale.PaymentMethod.UNKNOWN).aggregate(
        revenue=Sum('total', default=0), count=Count(Coalesce('order_token', 'token'), distinct=True))
    groups = []
    for label, field in [('Dorilar', 'name'), ('Xodimlar', 'shift__user__username'), ('Smenalar', 'shift_id')]:
        fields = ('placement__medicine_id', 'name', 'dosage') if label == 'Dorilar' else (field,)
        rows = sales.values(*fields).annotate(packages=Sum('quantity'), revenue=Sum('total')).order_by('-packages' if label == 'Dorilar' else '-revenue')
        groups.append((gettext_lazy(label), [(f"{r['name']} · {r['dosage']}" if label == 'Dorilar' else r[field], r['packages'], r['revenue']) for r in rows]))
    return render(request, 'catalog/reports.html', {'form': form, 'groups': groups, 'cash_totals': cash_totals, 'unknown_totals': unknown_totals, 'totals': sales.aggregate(packages=Sum('quantity', default=0), revenue=Sum('total', default=0))})
