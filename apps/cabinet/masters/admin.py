from django.contrib import admin
from .models import MasterProfile, Salon, Service


@admin.register(MasterProfile)
class MasterProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'slug', 'phone', 'created_at')
    search_fields = ('display_name', 'user__email', 'slug')
    prepopulated_fields = {'slug': ('display_name',)}


@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'address', 'phone', 'created_at')
    search_fields = ('name', 'owner__email', 'address')
    list_filter = ('created_at',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'salon', 'duration_min', 'price', 'is_active')
    search_fields = ('name', 'owner__email', 'salon__name')
    list_filter = ('is_active', 'salon')
