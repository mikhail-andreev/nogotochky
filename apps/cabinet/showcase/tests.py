from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from masters.models import MasterProfile, Salon, Service
from schedule.models import ScheduleSlot, Booking
from showcase.views import MasterSlotsView


def make_slot(owner, start, minutes=30, status=ScheduleSlot.Status.AVAILABLE):
    end = start + timedelta(minutes=minutes)
    return ScheduleSlot.objects.create(owner=owner, start_at=start, end_at=end, status=status)


def tomorrow_at(hour, minute=0):
    return (timezone.now() + timedelta(days=1)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


class MastersCatalogViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='cat@test.com', username='cat', password='pass123',
            role=User.Role.MASTER
        )
        self.profile = self.user.master_profile

    def test_catalog_page_loads(self):
        resp = self.client.get(reverse('masters_catalog'))
        self.assertEqual(resp.status_code, 200)

    def test_master_with_slots_appears(self):
        make_slot(self.user, tomorrow_at(10))
        resp = self.client.get(reverse('masters_catalog'))
        self.assertIn(self.profile, resp.context['masters'])

    def test_master_without_slots_not_in_main_list(self):
        resp = self.client.get(reverse('masters_catalog'))
        self.assertNotIn(self.profile, resp.context['masters'])

    def test_all_masters_always_present(self):
        resp = self.client.get(reverse('masters_catalog'))
        self.assertIn(self.profile, resp.context['all_masters'])

    def test_past_slots_not_counted(self):
        yesterday = timezone.now() - timedelta(days=1)
        make_slot(self.user, yesterday)
        resp = self.client.get(reverse('masters_catalog'))
        self.assertNotIn(self.profile, resp.context['masters'])


class MasterPageViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='mp@test.com', username='mp', password='pass123',
            role=User.Role.MASTER
        )
        self.profile = self.user.master_profile
        self.salon = Salon.objects.create(owner=self.user, name='Салон')
        self.service = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Маникюр', duration_min=60, price=2000
        )

    def test_master_page_loads(self):
        resp = self.client.get(reverse('master_page', args=[self.profile.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['profile'], self.profile)

    def test_master_page_shows_services(self):
        resp = self.client.get(reverse('master_page', args=[self.profile.slug]))
        self.assertIn(self.service, resp.context['services'])

    def test_inactive_service_hidden(self):
        self.service.is_active = False
        self.service.save()
        resp = self.client.get(reverse('master_page', args=[self.profile.slug]))
        self.assertNotIn(self.service, resp.context['services'])

    def test_nonexistent_slug_404(self):
        resp = self.client.get(reverse('master_page', args=['nonexistent']))
        self.assertEqual(resp.status_code, 404)


class MasterSlotsViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='ms@test.com', username='ms', password='pass123',
            role=User.Role.MASTER
        )
        self.profile = self.user.master_profile
        self.salon = Salon.objects.create(owner=self.user, name='Салон')
        self.service = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Маникюр', duration_min=60, price=2000
        )

    def test_slots_page_loads(self):
        resp = self.client.get(reverse('master_slots', args=[self.profile.slug]))
        self.assertEqual(resp.status_code, 200)

    def test_shows_available_slots(self):
        slot = make_slot(self.user, tomorrow_at(10))
        resp = self.client.get(reverse('master_slots', args=[self.profile.slug]))
        self.assertIn(slot, resp.context['slots'])

    def test_hides_booked_slots(self):
        make_slot(self.user, tomorrow_at(10), status=ScheduleSlot.Status.BOOKED)
        resp = self.client.get(reverse('master_slots', args=[self.profile.slug]))
        self.assertEqual(len(resp.context['slots']), 0)

    def test_with_service_filter(self):
        # 60 min service needs 2 consecutive 30-min slots
        slot1 = make_slot(self.user, tomorrow_at(10))
        slot2 = make_slot(self.user, tomorrow_at(10, 30))
        resp = self.client.get(
            reverse('master_slots', args=[self.profile.slug]),
            {'service': self.service.pk}
        )
        self.assertEqual(resp.context['service'], self.service)
        self.assertIn(slot1, resp.context['slots'])

    def test_single_slot_not_enough_for_long_service(self):
        # Only 1 slot, but service needs 2
        make_slot(self.user, tomorrow_at(10))
        resp = self.client.get(
            reverse('master_slots', args=[self.profile.slug]),
            {'service': self.service.pk}
        )
        self.assertEqual(len(resp.context['slots']), 0)


class FilterBookableSlotsTest(TestCase):
    """Unit tests for _filter_bookable_slots static method."""

    def _make_fake_slot(self, start, minutes=30):
        class FakeSlot:
            def __init__(self, s, e):
                self.start_at = s
                self.end_at = e
        return FakeSlot(start, start + timedelta(minutes=minutes))

    def test_slots_needed_1_returns_all(self):
        base = timezone.now()
        slots = [self._make_fake_slot(base + timedelta(minutes=i * 30)) for i in range(3)]
        result = MasterSlotsView._filter_bookable_slots(slots, 1)
        self.assertEqual(len(result), 3)

    def test_consecutive_slots_found(self):
        base = timezone.now()
        slots = [self._make_fake_slot(base + timedelta(minutes=i * 30)) for i in range(4)]
        result = MasterSlotsView._filter_bookable_slots(slots, 3)
        # slots 0, 1 can start a 3-slot sequence
        self.assertEqual(len(result), 2)

    def test_gap_breaks_sequence(self):
        base = timezone.now()
        slot1 = self._make_fake_slot(base)
        slot2 = self._make_fake_slot(base + timedelta(minutes=60))  # gap!
        result = MasterSlotsView._filter_bookable_slots([slot1, slot2], 2)
        self.assertEqual(len(result), 0)


class BookingCreateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='bc@test.com', username='bc', password='pass123',
            role=User.Role.MASTER
        )
        self.profile = self.user.master_profile
        self.salon = Salon.objects.create(owner=self.user, name='Салон')
        self.service = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Маникюр', duration_min=30, price=1500
        )
        self.slot = make_slot(self.user, tomorrow_at(10))

    def test_booking_form_loads(self):
        resp = self.client.get(
            reverse('booking_create', args=[self.profile.slug]),
            {'service': self.service.pk, 'slot': self.slot.pk}
        )
        self.assertEqual(resp.status_code, 200)

    def test_successful_booking(self):
        resp = self.client.post(
            reverse('booking_create', args=[self.profile.slug]),
            {
                'service_id': self.service.pk,
                'slot_id': self.slot.pk,
                'client_name': 'Тест Клиент',
                'client_phone': '+7 999 000-00-00',
                'notes': '',
            }
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn('success', resp.url)

        booking = Booking.objects.get(owner=self.user)
        self.assertEqual(booking.client_name, 'Тест Клиент')
        self.assertEqual(booking.service, self.service)

        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, ScheduleSlot.Status.BOOKED)

    def test_multi_slot_booking(self):
        # 60 min service, 30 min slots — needs 2 slots
        long_service = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Педикюр', duration_min=60, price=2500
        )
        slot1 = make_slot(self.user, tomorrow_at(14))
        slot2 = make_slot(self.user, tomorrow_at(14, 30))

        resp = self.client.post(
            reverse('booking_create', args=[self.profile.slug]),
            {
                'service_id': long_service.pk,
                'slot_id': slot1.pk,
                'client_name': 'Мульти',
                'client_phone': '+7 000',
                'notes': '',
            }
        )
        self.assertEqual(resp.status_code, 302)

        booking = Booking.objects.get(client_name='Мульти')
        self.assertEqual(booking.booked_slots.count(), 2)

        slot1.refresh_from_db()
        slot2.refresh_from_db()
        self.assertEqual(slot1.status, ScheduleSlot.Status.BOOKED)
        self.assertEqual(slot2.status, ScheduleSlot.Status.BOOKED)

    def test_booking_already_booked_slot_fails(self):
        self.slot.status = ScheduleSlot.Status.BOOKED
        self.slot.save()

        resp = self.client.post(
            reverse('booking_create', args=[self.profile.slug]),
            {
                'service_id': self.service.pk,
                'slot_id': self.slot.pk,
                'client_name': 'Неудача',
                'client_phone': '+7 000',
                'notes': '',
            }
        )
        self.assertEqual(resp.status_code, 200)  # re-renders form
        self.assertEqual(Booking.objects.count(), 0)

    def test_booking_not_enough_consecutive_slots(self):
        long_service = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Длинная', duration_min=90, price=3000
        )
        # Only 1 slot available, need 3
        single_slot = make_slot(self.user, tomorrow_at(16))

        resp = self.client.post(
            reverse('booking_create', args=[self.profile.slug]),
            {
                'service_id': long_service.pk,
                'slot_id': single_slot.pk,
                'client_name': 'Нехватка',
                'client_phone': '+7 000',
                'notes': '',
            }
        )
        self.assertEqual(resp.status_code, 200)  # form with error
        self.assertEqual(Booking.objects.count(), 0)


class BookingSuccessViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='bs@test.com', username='bs', password='pass123',
            role=User.Role.MASTER
        )
        self.profile = self.user.master_profile
        self.salon = Salon.objects.create(owner=self.user, name='Салон')
        self.service = Service.objects.create(
            owner=self.user, salon=self.salon,
            name='Маникюр', duration_min=30, price=1500
        )
        self.slot = make_slot(self.user, tomorrow_at(10), status=ScheduleSlot.Status.BOOKED)
        self.booking = Booking.objects.create(
            owner=self.user, service=self.service, slot=self.slot,
            client_name='Успех', client_phone='+7 000'
        )

    def test_success_page_loads(self):
        resp = self.client.get(
            reverse('booking_success', args=[self.profile.slug]),
            {'booking': self.booking.pk}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['booking'], self.booking)

    def test_success_page_without_booking_id(self):
        resp = self.client.get(reverse('booking_success', args=[self.profile.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context.get('booking'))
