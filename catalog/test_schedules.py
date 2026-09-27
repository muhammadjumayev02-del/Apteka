from datetime import timedelta
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Shift, ShiftSchedule


class ScheduleTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name='Aptekachi')
        self.worker = User.objects.create_user('scheduled_worker')
        self.worker.groups.add(group)
        self.other = User.objects.create_user('other_worker')
        self.other.groups.add(group)
        self.admin = User.objects.create_superuser('owner')
        self.start = timezone.now().replace(second=0, microsecond=0)
        self.end = self.start + timedelta(hours=8)
        self.url = reverse('catalog:schedule_create')
        self.shifts = reverse('catalog:shifts')

    def data(self, start=None, end=None):
        return {'user': self.worker.pk,
                'planned_start': timezone.localtime(start or self.start).strftime('%Y-%m-%dT%H:%M'),
                'planned_end': timezone.localtime(end or self.end).strftime('%Y-%m-%dT%H:%M')}

    def test_schedule_permissions_validation_and_overnight(self):
        self.client.force_login(self.worker)
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)
        self.client.force_login(self.admin)
        self.assertContains(self.client.post(self.url, self.data(end=self.start)), 'Tugash vaqti')
        self.assertEqual(self.client.post(self.url, self.data(end=self.start + timedelta(days=1))).status_code, 302)
        self.assertContains(self.client.post(self.url, self.data()), 'boshqa smenasi bor')
        self.assertEqual(ShiftSchedule.objects.count(), 1)
        schedule = ShiftSchedule.objects.get()
        self.assertEqual(schedule.planned_start, self.start)
        self.assertEqual(self.client.post(self.url, self.data(start=schedule.planned_end, end=schedule.planned_end + timedelta(hours=8))).status_code, 302)

    def test_planned_actual_times_isolation_and_repeat_start(self):
        schedule = ShiftSchedule.objects.create(user=self.worker, planned_start=self.start, planned_end=self.end)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(self.shifts), self.worker.username)
        self.assertEqual(self.client.post(self.shifts, {'action': 'start', 'schedule': schedule.pk}).status_code, 403)
        self.client.force_login(self.worker)
        self.assertNotContains(self.client.get(self.shifts), 'Smenani boshlash')
        self.assertEqual(self.client.post(self.shifts, {'action': 'start'}).status_code, 403)
        self.client.force_login(self.admin)
        for _ in range(2):
            self.client.post(self.shifts, {'action': 'start', 'schedule': schedule.pk})
        shift = Shift.objects.get(schedule=schedule)
        self.assertIsNotNone(shift.started_at)
        self.client.post(self.shifts, {'action': 'end', 'shift': shift.pk})
        shift.refresh_from_db()
        ended = shift.ended_at
        self.client.post(self.shifts, {'action': 'end', 'shift': shift.pk})
        self.client.post(self.shifts, {'action': 'start', 'schedule': schedule.pk})
        shift.refresh_from_db()
        schedule.refresh_from_db()
        self.assertEqual(shift.ended_at, ended)
        self.assertEqual(Shift.objects.count(), 1)
        self.assertEqual(schedule.planned_start, self.start)
        self.assertEqual(schedule.planned_end, self.end)
        self.client.force_login(self.admin)
        response = self.client.get(self.shifts)
        for text in (self.worker.username, 'Reja:', 'Haqiqiy:', 'Ishlagan vaqt:', '0 sotuv'):
            self.assertContains(response, text)
