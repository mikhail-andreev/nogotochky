from django.urls import path
from . import views

urlpatterns = [
    path('', views.MastersCatalogView.as_view(), name='masters_catalog'),
    path('<slug:slug>/', views.MasterPageView.as_view(), name='master_page'),
    path('<slug:slug>/slots/', views.MasterSlotsView.as_view(), name='master_slots'),
    path('<slug:slug>/book/', views.BookingCreateView.as_view(), name='booking_create'),
    path('<slug:slug>/book/success/', views.BookingSuccessView.as_view(), name='booking_success'),
]
