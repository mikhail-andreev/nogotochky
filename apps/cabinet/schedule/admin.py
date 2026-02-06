from django.contrib import admin
from .models import ScheduleSlot, Booking


@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ('owner', 'start_at', 'end_at', 'status')
    list_filter = ('status', 'owner', 'start_at')
    search_fields = ('owner__email',)
    date_hierarchy = 'start_at'


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'client_phone', 'service', 'owner', 'slot', 'status', 'created_at')
    list_filter = ('status', 'owner', 'created_at')
    search_fields = ('client_name', 'client_phone', 'owner__email')
    date_hierarchy = 'created_at'
