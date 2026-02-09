from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from masters.models import Salon, Service
from .models import ScheduleSlot, Booking
from .forms import SlotCreateForm


def make_slot(owner, start, minutes=30, status=ScheduleSlot.Status.AVAILABLE):
    end = start + timedelta(minutes=minutes)
    return ScheduleSlot.objects.create(owner=owner, start_at=start, end_at=end, status=status)


class ScheduleSlotModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='slot@test.com', username='slot', password='pass123',
            role=User.Role.MASTER
        )

    def test_duration_minutes(self):
        now = timezone.now()
        slot = make_slot(self.user, now, minutes=45)
        self.assertEqual(slot.duration_minutes, 45)

    def test_is_available(self):
        now = timezone.now()
        slot = make_slot(self.user, now)
        self.assertTrue(slot.is_available)
        slot.status = ScheduleSlot.Status.BOOKED
        self.assertFalse(slot.is_available)

    def test_str(self):
        now = timezone.now()
        slot = make_slot(self.user, now)
        self.assertIn('-', str(slot))


class BookingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='bk@test.com', username='bk', password='pass123',
            role=User.Role.MASTER
        )
        self.salon = Salon.objects.create(owner=self.user, name='Салон')
        self.service = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Маникюр', duration_min=30, price=1500
        )
        tomorrow = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.slot = make_slot(self.user, tomorrow)

    def test_create_booking(self):
        booking = Booking.objects.create(
            owner=self.user, service=self.service, slot=self.slot,
            client_name='Клиент', client_phone='+7999'
        )
        self.assertEqual(booking.status, Booking.Status.CREATED)
        self.assertIn('Клиент', str(booking))

    def test_cancel_booking(self):
        self.slot.status = ScheduleSlot.Status.BOOKED
        self.slot.save()

        booking = Booking.objects.create(
            owner=self.user, service=self.service, slot=self.slot,
            client_name='Клиент', client_phone='+7999'
        )
        booking.booked_slots.set([self.slot])

        booking.cancel()
        booking.refresh_from_db()
        self.slot.refresh_from_db()

        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertEqual(self.slot.status, ScheduleSlot.Status.AVAILABLE)

    def test_cancel_multi_slot_booking(self):
        tomorrow = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
        slot1 = make_slot(self.user, tomorrow)
        slot2 = make_slot(self.user, tomorrow + timedelta(minutes=30))
        slot3 = make_slot(self.user, tomorrow + timedelta(minutes=60))

        for s in [slot1, slot2, slot3]:
            s.status = ScheduleSlot.Status.BOOKED
            s.save()

        booking = Booking.objects.create(
            owner=self.user, service=self.service, slot=slot1,
            client_name='Клиент', client_phone='+7999'
        )
        booking.booked_slots.set([slot1, slot2, slot3])

        booking.cancel()

        for s in [slot1, slot2, slot3]:
            s.refresh_from_db()
            self.assertEqual(s.status, ScheduleSlot.Status.AVAILABLE)


class SlotCreateFormTest(TestCase):
    def test_valid_form(self):
        form = SlotCreateForm(data={
            'date': '2026-03-01',
            'start_time': '10:00',
            'end_time': '12:00',
            'slot_duration': 30,
        })
        self.assertTrue(form.is_valid())

    def test_end_before_start_invalid(self):
        form = SlotCreateForm(data={
            'date': '2026-03-01',
            'start_time': '14:00',
            'end_time': '10:00',
            'slot_duration': 30,
        })
        self.assertFalse(form.is_valid())

    def test_generate_slots(self):
        user = User.objects.create_user(
            email='gen@test.com', username='gen', password='pass123',
            role=User.Role.MASTER
        )
        form = SlotCreateForm(data={
            'date': '2026-03-01',
            'start_time': '10:00',
            'end_time': '12:00',
            'slot_duration': 30,
        })
        form.is_valid()
        count = form.generate_slots(user)
        self.assertEqual(count, 4)  # 10:00, 10:30, 11:00, 11:30
        self.assertEqual(ScheduleSlot.objects.filter(owner=user).count(), 4)


class SlotViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='slv@test.com', username='slv', password='pass123',
            role=User.Role.MASTER
        )
        self.client.login(username='slv@test.com', password='pass123')

    def test_slot_list(self):
        resp = self.client.get(reverse('slot_list'))
        self.assertEqual(resp.status_code, 200)

    def test_slot_create(self):
        resp = self.client.post(reverse('slot_create'), {
            'date': '2026-03-15',
            'start_time': '09:00',
            'end_time': '11:00',
            'slot_duration': 30,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ScheduleSlot.objects.filter(owner=self.user).count(), 4)

    def test_slot_delete(self):
        tomorrow = timezone.now() + timedelta(days=1)
        slot = make_slot(self.user, tomorrow)
        resp = self.client.post(reverse('slot_delete', args=[slot.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ScheduleSlot.objects.filter(pk=slot.pk).exists())

    def test_cannot_delete_booked_slot(self):
        tomorrow = timezone.now() + timedelta(days=1)
        slot = make_slot(self.user, tomorrow, status=ScheduleSlot.Status.BOOKED)
        resp = self.client.post(reverse('slot_delete', args=[slot.pk]))
        self.assertEqual(resp.status_code, 404)


class BookingViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='bkv@test.com', username='bkv', password='pass123',
            role=User.Role.MASTER
        )
        self.salon = Salon.objects.create(owner=self.user, name='Салон')
        self.service = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Маникюр', duration_min=30, price=1500
        )
        self.client.login(username='bkv@test.com', password='pass123')

    def test_booking_list(self):
        resp = self.client.get(reverse('booking_list'))
        self.assertEqual(resp.status_code, 200)

    def test_booking_cancel(self):
        tomorrow = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        slot = make_slot(self.user, tomorrow, status=ScheduleSlot.Status.BOOKED)
        booking = Booking.objects.create(
            owner=self.user, service=self.service, slot=slot,
            client_name='Клиент', client_phone='+7999'
        )
        booking.booked_slots.set([slot])

        resp = self.client.post(reverse('booking_cancel', args=[booking.pk]))
        self.assertEqual(resp.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_cannot_cancel_other_master_booking(self):
        other = User.objects.create_user(
            email='oth@test.com', username='oth', password='pass123',
            role=User.Role.MASTER
        )
        other_salon = Salon.objects.create(owner=other, name='Другой')
        other_svc = Service.objects.create(
            owner=other, salon=other_salon, name='Сервис', duration_min=30, price=500
        )
        tomorrow = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
        slot = make_slot(other, tomorrow, status=ScheduleSlot.Status.BOOKED)
        booking = Booking.objects.create(
            owner=other, service=other_svc, slot=slot,
            client_name='Чужой', client_phone='+7000'
        )
        resp = self.client.post(reverse('booking_cancel', args=[booking.pk]))
        self.assertEqual(resp.status_code, 404)
