from datetime import datetime, timedelta

from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, FormView

from masters.models import MasterProfile, Service
from schedule.models import ScheduleSlot, Booking
from .forms import PublicBookingForm


class MasterPageView(TemplateView):
    """Public master page with profile, salon and services."""
    template_name = 'showcase/master_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['slug']

        profile = get_object_or_404(MasterProfile, slug=slug)
        context['profile'] = profile
        context['salon'] = profile.user.salons.first()
        context['services'] = Service.objects.filter(
            owner=profile.user,
            is_active=True
        )
        return context


class MasterSlotsView(TemplateView):
    """Available slots for master."""
    template_name = 'showcase/master_slots.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['slug']

        profile = get_object_or_404(MasterProfile, slug=slug)
        context['profile'] = profile

        # Get service if specified
        service_id = self.request.GET.get('service')
        if service_id:
            context['service'] = get_object_or_404(
                Service,
                pk=service_id,
                owner=profile.user,
                is_active=True
            )

        # Date range filter
        date_from = self.request.GET.get('from')
        date_to = self.request.GET.get('to')

        slots = ScheduleSlot.objects.filter(
            owner=profile.user,
            status=ScheduleSlot.Status.AVAILABLE
        )

        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d')
                slots = slots.filter(start_at__date__gte=date_from)
            except ValueError:
                pass
        else:
            # Default: from today
            slots = slots.filter(start_at__gte=timezone.now())

        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d')
                slots = slots.filter(start_at__date__lte=date_to)
            except ValueError:
                pass
        else:
            # Default: next 14 days
            slots = slots.filter(start_at__date__lte=timezone.now().date() + timedelta(days=14))

        all_slots = list(slots.order_by('start_at'))

        # Filter: only show slots where enough consecutive slots exist for the service
        service = context.get('service')
        if service and all_slots:
            slot_duration = all_slots[0].duration_minutes if all_slots else 30
            slots_needed = max(1, -(-service.duration_min // slot_duration))  # ceil division
            context['slots'] = self._filter_bookable_slots(all_slots, slots_needed)
        else:
            context['slots'] = all_slots

        return context

    @staticmethod
    def _filter_bookable_slots(slots, slots_needed):
        """Return only slots that have enough consecutive available slots after them."""
        if slots_needed <= 1:
            return slots

        bookable = []
        for i, slot in enumerate(slots):
            consecutive = 1
            for j in range(i + 1, min(i + slots_needed, len(slots))):
                if slots[j].start_at == slots[j - 1].end_at:
                    consecutive += 1
                else:
                    break
            if consecutive >= slots_needed:
                bookable.append(slot)
        return bookable


class BookingCreateView(FormView):
    """Create booking from public storefront."""
    template_name = 'showcase/booking_form.html'
    form_class = PublicBookingForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['slug']

        profile = get_object_or_404(MasterProfile, slug=slug)
        context['profile'] = profile

        # Pre-fill service and slot from GET params
        service_id = self.request.GET.get('service')
        slot_id = self.request.GET.get('slot')

        if service_id:
            context['service'] = get_object_or_404(
                Service, pk=service_id, owner=profile.user, is_active=True
            )
        if slot_id:
            context['slot'] = get_object_or_404(
                ScheduleSlot, pk=slot_id, owner=profile.user, status=ScheduleSlot.Status.AVAILABLE
            )

        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['service_id'] = self.request.GET.get('service', '')
        initial['slot_id'] = self.request.GET.get('slot', '')
        return initial

    def form_valid(self, form):
        slug = self.kwargs['slug']
        profile = get_object_or_404(MasterProfile, slug=slug)

        service_id = form.cleaned_data['service_id']
        slot_id = form.cleaned_data['slot_id']

        service = get_object_or_404(
            Service, pk=service_id, owner=profile.user, is_active=True
        )

        try:
            booking = self._create_booking(
                owner=profile.user,
                service=service,
                slot_id=slot_id,
                client_name=form.cleaned_data['client_name'],
                client_phone=form.cleaned_data['client_phone'],
                notes=form.cleaned_data.get('notes', '')
            )
            return redirect(reverse('booking_success', kwargs={'slug': slug}) + f'?booking={booking.id}')
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        except IntegrityError:
            form.add_error(None, 'Этот слот уже занят. Пожалуйста, выберите другое время.')
            return self.form_invalid(form)

    @transaction.atomic
    def _create_booking(self, owner, service, slot_id, client_name, client_phone, notes):
        """Create booking with transaction. Locks multiple consecutive slots if needed."""
        # Lock the starting slot
        start_slot = ScheduleSlot.objects.select_for_update().get(pk=slot_id, owner=owner)

        if start_slot.status != ScheduleSlot.Status.AVAILABLE:
            raise ValueError('Слот уже занят')

        if service.owner_id != start_slot.owner_id:
            raise ValueError('Услуга и слот принадлежат разным мастерам')

        # Calculate how many slots are needed
        slot_duration = start_slot.duration_minutes
        slots_needed = max(1, -(-service.duration_min // slot_duration))  # ceil division

        # Find and lock consecutive slots
        slots_to_book = [start_slot]
        if slots_needed > 1:
            next_slots = list(
                ScheduleSlot.objects.select_for_update()
                .filter(
                    owner=owner,
                    status=ScheduleSlot.Status.AVAILABLE,
                    start_at__gt=start_slot.start_at,
                    start_at__lte=start_slot.start_at + timedelta(minutes=slot_duration * (slots_needed - 1))
                )
                .order_by('start_at')
            )

            # Verify slots are consecutive
            current_end = start_slot.end_at
            for ns in next_slots:
                if ns.start_at == current_end:
                    slots_to_book.append(ns)
                    current_end = ns.end_at
                else:
                    break

            if len(slots_to_book) < slots_needed:
                raise ValueError(
                    f'Недостаточно последовательных свободных слотов. '
                    f'Нужно: {slots_needed}, доступно: {len(slots_to_book)}'
                )

        # Create booking linked to start slot
        booking = Booking.objects.create(
            owner=owner,
            service=service,
            slot=start_slot,
            client_name=client_name,
            client_phone=client_phone,
            notes=notes
        )

        # Mark all slots as booked and link to booking
        for s in slots_to_book:
            s.status = ScheduleSlot.Status.BOOKED
            s.save()
        booking.booked_slots.set(slots_to_book)

        return booking


class BookingSuccessView(TemplateView):
    """Booking confirmation page."""
    template_name = 'showcase/booking_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['slug']

        profile = get_object_or_404(MasterProfile, slug=slug)
        context['profile'] = profile

        booking_id = self.request.GET.get('booking')
        if booking_id:
            context['booking'] = Booking.objects.filter(
                pk=booking_id,
                owner=profile.user
            ).select_related('service', 'slot').first()

        return context
