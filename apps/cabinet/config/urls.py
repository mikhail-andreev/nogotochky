"""
URL configuration for master-portal project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    # Home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Django Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('auth/', include('accounts.urls')),

    # Master cabinet
    path('cabinet/', include('masters.urls')),
    path('cabinet/schedule/', include('schedule.urls')),

    # Public storefront
    path('masters/', include('showcase.urls')),
]
