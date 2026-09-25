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
        raise ValidationError(gettext_lazy('Smena yopilgan. Yangi smena boshlang.'))
    existing = Sale.objects.filter(token=data['token'], shift__user=user).first()
    if existing:
        return existing
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
                               **data['product'], quantity=count, unit_price=medicine.price, total=medicine.price * count)


@transaction.atomic
def transfer_stock(user, medicine, data):
    Medicine.objects.select_for_update().get(pk=medicine.pk)
    source = Placement.objects.select_for_update().get(pk=data['source'].pk, medicine=medicine)
    count = data['quantity']
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
    # Read immutable sale values from the database, not a potentially stale caller.
    if not Sale.objects.filter(pk=sale.pk, cancelled_at__isnull=True).update(cancelled_at=timezone.now(), cancelled_by=user):
        return False
    saved = Sale.objects.get(pk=sale.pk)
    Placement.objects.filter(pk=saved.placement_id).update(quantity=F('quantity') + saved.quantity)
    return True
