from django.utils.translation import gettext_lazy
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import Medicine, Placement, Batch, Sale, Shift, StockTransfer


def validate_expiry(batch):
    if batch.expires_on is None:
        raise ValidationError(gettext_lazy('Sotuvdan oldin partiyaning yaroqlilik sanasini kiriting.'))
    if batch.expires_on < timezone.localdate():
        raise ValidationError(gettext_lazy('Partiyaning yaroqlilik muddati o‘tgan. Sotish mumkin emas.'))


def snapshot(medicine):
    return {key: getattr(medicine, key) for key in ('name', 'dosage', 'form', 'package_size')}


@transaction.atomic
def confirm_sale(user, data):
    # A write on the shift serializes confirmation/closing on SQLite as well.
    if not Shift.objects.filter(pk=data['shift'], user=user, ended_at__isnull=True).update(ended_at=None):
        raise ValidationError(gettext_lazy('Sotuv uchun smenani admin ochishi kerak.'))
    existing = Sale.objects.filter(token=data['token'], shift__user=user).first()
    if existing:
        return existing
    if data.get('payment_method') not in (Sale.PaymentMethod.CASH, Sale.PaymentMethod.CARD):
        raise ValidationError(gettext_lazy('To‘lov usulini tanlang.'))
    medicine = Medicine.objects.select_for_update().get(pk=data['medicine'])
    if snapshot(medicine) != data['product'] or str(medicine.price) != data['price']:
        raise ValidationError(gettext_lazy('Mahsulot yoki narx o‘zgargan. Sotuvni qaytadan tekshiring.'))
    place = Placement.objects.select_for_update().filter(pk=data['placement'], medicine=medicine).first()
    if not place or place.location_key != data['location'] or place.batch_id != data['batch']:
        raise ValidationError(gettext_lazy('Partiya yoki joylashuv o‘zgargan. Sotuvni qaytadan tekshiring.'))
    batch = Batch.objects.select_for_update().get(pk=place.batch_id)
    validate_expiry(batch)
    count = data['quantity']
    if count < 1 or not Placement.objects.filter(pk=data['placement'], medicine=medicine, quantity__gte=count).update(quantity=F('quantity') - count):
        raise ValidationError(gettext_lazy('Qoldiq yetarli emas. Sotuvni qaytadan tekshiring.'))
    return Sale.objects.create(token=data['token'], shift_id=data['shift'], placement_id=data['placement'],
                               **data['product'], payment_method=data['payment_method'], quantity=count, unit_price=medicine.price, total=medicine.price * count)


@transaction.atomic
def transfer_stock(user, medicine, data):
    Medicine.objects.select_for_update().get(pk=medicine.pk)
    source = Placement.objects.select_for_update().get(pk=data['source'].pk, medicine=medicine)
    count = data['quantity']
    if count < 1:
        raise ValidationError(gettext_lazy('To‘g‘ri qiymat kiriting.'))
    coordinates = {k: data[k] for k in ('department', 'shelf', 'row')}
    if all(getattr(source, k) == v for k, v in coordinates.items()):
        raise ValidationError(gettext_lazy('Manba va yangi joy bir xil bo‘lishi mumkin emas.'))
    if not Placement.objects.filter(pk=source.pk, medicine=medicine, quantity__gte=count).update(quantity=F('quantity') - count):
        raise ValidationError(gettext_lazy('Manba joyda qoldiq yetarli emas.'))
    source.refresh_from_db()
    destination, _ = Placement.objects.get_or_create(medicine=medicine, batch=source.batch, **coordinates, defaults={'quantity': 0})
    Placement.objects.filter(pk=destination.pk).update(quantity=F('quantity') + count)
    return StockTransfer.objects.create(source=source, destination=destination, source_label=source.location_key,
                                         destination_label=destination.location_key, quantity=count, user=user)


@transaction.atomic
def cancel_sale(sale, user):
    saved = Sale.objects.get(pk=sale.pk)
    from django.core.exceptions import PermissionDenied
    if not user.is_active or (not user.is_superuser and saved.shift.user_id != user.pk):
        raise PermissionDenied
    # Lock the shift before reading the receipt, serializing repeated cancellations.
    Shift.objects.filter(pk=saved.shift_id).update(ended_at=F('ended_at'))
    lines = Sale.objects.filter(order_token=saved.order_token) if saved.order_token else Sale.objects.filter(pk=saved.pk)
    pending = list(lines.filter(cancelled_at__isnull=True).order_by('placement_id', 'pk'))
    for line in pending:
        if Sale.objects.filter(pk=line.pk, cancelled_at__isnull=True).update(cancelled_at=timezone.now(), cancelled_by=user):
            Placement.objects.filter(pk=line.placement_id).update(quantity=F('quantity') + line.quantity)
    return bool(pending)


@transaction.atomic
def confirm_cart(user, lines, token):
    from .roles import can_view_catalog
    if not can_view_catalog(user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    existing = Sale.objects.filter(order_token=token, shift__user=user)
    if existing.exists():
        return list(existing)
    if not lines or len(lines) > 100:
        raise ValidationError(gettext_lazy('Savat bo‘sh yoki juda katta.'))
    sales = []
    for line in sorted(lines, key=lambda item: (item['medicine'], item['placement'])):
        sales.append(confirm_sale(user, line))
    Sale.objects.filter(pk__in=[s.pk for s in sales]).update(order_token=token)
    return sales


@transaction.atomic
def receive_stock(user, placement, quantity, received_on):
    from .models import StockReceipt
    from django.core.exceptions import PermissionDenied
    if not user.is_active or not user.is_superuser:
        raise PermissionDenied
    if quantity < 1 or received_on > timezone.localdate():
        raise ValidationError(gettext_lazy('To‘g‘ri qiymat kiriting.'))
    Placement.objects.filter(pk=placement.pk).update(quantity=F('quantity') + quantity)
    Batch.objects.filter(pk=placement.batch_id, received_on__isnull=True).update(received_on=received_on)
    return StockReceipt.objects.create(user=user, placement=placement, quantity=quantity, received_on=received_on)
