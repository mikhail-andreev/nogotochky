from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, FormView, DeleteView, View

from masters.views import MasterRequiredMixin
from .models import ScheduleSlot, Booking
from .forms import SlotCreateForm


# Slot views
class SlotListView(MasterRequiredMixin, ListView):
    """List master's schedule slots."""
    model = ScheduleSlot
    template_name = 'schedule/slot_list.html'
    context_object_name = 'slots'

    def get_queryset(self):
        queryset = ScheduleSlot.objects.filter(owner=self.request.user)

        # Filter by date range
        date_from = self.request.GET.get('from')
        date_to = self.request.GET.get('to')

        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(start_at__date__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(start_at__date__lte=date_to)
            except ValueError:
                pass

        # Default: show slots from today
        if not date_from and not date_to:
            queryset = queryset.filter(start_at__date__gte=timezone.now().date())

        return queryset.order_by('start_at')


class SlotCreateView(MasterRequiredMixin, FormView):
    """Create schedule slots."""
    form_class = SlotCreateForm
    template_name = 'schedule/slot_form.html'
    success_url = reverse_lazy('slot_list')

    def form_valid(self, form):
        count = form.generate_slots(self.request.user)
        messages.success(self.request, f'Создано слотов: {count}')
        return super().form_valid(form)


class SlotDeleteView(MasterRequiredMixin, DeleteView):
    """Delete a slot."""
    model = ScheduleSlot
    template_name = 'schedule/slot_confirm_delete.html'
    success_url = reverse_lazy('slot_list')

    def get_queryset(self):
        return ScheduleSlot.objects.filter(
            owner=self.request.user,
            status=ScheduleSlot.Status.AVAILABLE
        )


# Booking views
class BookingListView(MasterRequiredMixin, ListView):
    """List master's bookings."""
    model = Booking
    template_name = 'schedule/booking_list.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        queryset = Booking.objects.filter(owner=self.request.user)

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related('service', 'slot')


class BookingDetailView(MasterRequiredMixin, DetailView):
    """View booking details."""
    model = Booking
    template_name = 'schedule/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        return Booking.objects.filter(owner=self.request.user).select_related('service', 'slot')


class BookingCancelView(MasterRequiredMixin, View):
    """Cancel a booking."""

    def post(self, request, pk):
        booking = get_object_or_404(
            Booking,
            pk=pk,
            owner=request.user,
            status=Booking.Status.CREATED
        )
        booking.cancel()
        messages.success(request, 'Запись отменена')
        return redirect('booking_list')
