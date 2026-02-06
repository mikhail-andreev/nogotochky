from django.urls import path
from . import views

urlpatterns = [
    # Slots
    path('slots/', views.SlotListView.as_view(), name='slot_list'),
    path('slots/create/', views.SlotCreateView.as_view(), name='slot_create'),
    path('slots/<int:pk>/delete/', views.SlotDeleteView.as_view(), name='slot_delete'),

    # Bookings
    path('bookings/', views.BookingListView.as_view(), name='booking_list'),
    path('bookings/<int:pk>/', views.BookingDetailView.as_view(), name='booking_detail'),
    path('bookings/<int:pk>/cancel/', views.BookingCancelView.as_view(), name='booking_cancel'),
]
