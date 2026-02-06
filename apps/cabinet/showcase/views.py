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

        context['slots'] = slots.order_by('start_at')
        return context


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
        """Create booking with transaction and slot locking."""
        # Lock the slot for update
        slot = ScheduleSlot.objects.select_for_update().get(pk=slot_id, owner=owner)

        if slot.status != ScheduleSlot.Status.AVAILABLE:
            raise ValueError('Слот уже занят')

        # Verify service and slot belong to same owner
        if service.owner_id != slot.owner_id:
            raise ValueError('Услуга и слот принадлежат разным мастерам')

        # Create booking
        booking = Booking.objects.create(
            owner=owner,
            service=service,
            slot=slot,
            client_name=client_name,
            client_phone=client_phone,
            notes=notes
        )

        # Update slot status
        slot.status = ScheduleSlot.Status.BOOKED
        slot.save()

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
