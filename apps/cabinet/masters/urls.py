from django.urls import path
from . import views

urlpatterns = [
    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),

    # Salon
    path('salon/', views.SalonView.as_view(), name='salon'),
    path('salon/edit/', views.SalonEditView.as_view(), name='salon_edit'),

    # Services
    path('services/', views.ServiceListView.as_view(), name='service_list'),
    path('services/create/', views.ServiceCreateView.as_view(), name='service_create'),
    path('services/<int:pk>/edit/', views.ServiceEditView.as_view(), name='service_edit'),
    path('services/<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),
]
