from django.utils.translation import gettext_lazy
from datetime import datetime, time, timedelta

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import Batch, Medicine, Sale, Shift, ShiftSchedule


def dashboard_context():
    """Database-backed metrics for the owner’s Django admin index."""
    now = timezone.now()
    today = timezone.localdate(now)
    start = timezone.make_aware(datetime.combine(today, time.min))
    end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))
    threshold = settings.PHARMACY_LOW_STOCK_THRESHOLD
    expiry_days = settings.PHARMACY_EXPIRY_WARNING_DAYS
    today_sales = Sale.objects.filter(created_at__gte=start, created_at__lt=end)
    valid_sales = today_sales.filter(cancelled_at__isnull=True)
    totals = valid_sales.aggregate(count=Count('pk'), packages=Sum('quantity', default=0), revenue=Sum('total', default=0))
    cash_totals = valid_sales.filter(payment_method=Sale.PaymentMethod.CASH).aggregate(
        revenue=Sum('total', default=0), count=Count(Coalesce('order_token', 'token'), distinct=True))
    low_stock = Medicine.objects.annotate(stock=Sum('placements__quantity', default=0)).filter(stock__lt=threshold).order_by('stock', 'name', 'pk')
    batches = Batch.objects.select_related('medicine').annotate(stock=Sum('placements__quantity', default=0)).filter(stock__gt=0).order_by('expires_on', 'pk')
    schedules = list(ShiftSchedule.objects.filter(planned_start__lt=end, planned_end__gt=start).select_related('user', 'shift').order_by('planned_start', 'pk'))
    rows = []
    for schedule in schedules:
        shift = getattr(schedule, 'shift', None)
        status = (gettext_lazy('Yakunlangan') if shift.ended_at else gettext_lazy('Ishlamoqda')) if shift else (gettext_lazy('Boshlanmagan — reja vaqti o‘tgan') if schedule.planned_start < now else gettext_lazy('Rejalashtirilgan'))
        rows.append({'user': schedule.user, 'schedule': schedule, 'shift': shift, 'status': status})
    actual_shifts = Shift.objects.filter(started_at__lt=end).filter(Q(ended_at__isnull=True) | Q(ended_at__gt=start)).exclude(schedule_id__in=[s.pk for s in schedules]).select_related('user', 'schedule')
    for shift in actual_shifts:
        rows.append({'user': shift.user, 'schedule': shift.schedule, 'shift': shift, 'status': gettext_lazy('Yakunlangan') if shift.ended_at else gettext_lazy('Ishlamoqda')})
    return {
        'today': today, 'totals': totals, 'cash_totals': cash_totals, 'threshold': threshold, 'expiry_days': expiry_days,
        'low_stock': low_stock, 'expired_batches': batches.filter(expires_on__lt=today),
        'expiring_batches': batches.filter(expires_on__gte=today, expires_on__lte=today + timedelta(days=expiry_days)),
        'unknown_expiry_count': batches.filter(expires_on__isnull=True).count(),
        'shift_rows': rows,
        'top_medicines': valid_sales.values('placement__medicine_id', 'placement__medicine__name', 'placement__medicine__dosage').annotate(packages=Sum('quantity'), revenue=Sum('total')).order_by('-packages', 'placement__medicine_id')[:5],
        'recent_sales': Sale.objects.select_related('shift__user').order_by('-created_at', '-pk')[:10],
    }
