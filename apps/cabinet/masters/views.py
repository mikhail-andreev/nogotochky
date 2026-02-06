from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView, ListView, CreateView, DeleteView

from .models import MasterProfile, Salon, Service
from .forms import MasterProfileForm, SalonForm, ServiceForm


class MasterRequiredMixin(LoginRequiredMixin):
    """Mixin that ensures user is a master."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_master:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


# Profile views
class ProfileView(MasterRequiredMixin, TemplateView):
    """View master profile."""
    template_name = 'masters/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(MasterProfile, user=self.request.user)
        return context


class ProfileEditView(MasterRequiredMixin, UpdateView):
    """Edit master profile."""
    model = MasterProfile
    form_class = MasterProfileForm
    template_name = 'masters/profile_form.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return get_object_or_404(MasterProfile, user=self.request.user)


# Salon views
class SalonView(MasterRequiredMixin, TemplateView):
    """View salon."""
    template_name = 'masters/salon.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['salon'] = Salon.objects.filter(owner=self.request.user).first()
        return context


class SalonEditView(MasterRequiredMixin, UpdateView):
    """Edit or create salon."""
    model = Salon
    form_class = SalonForm
    template_name = 'masters/salon_form.html'
    success_url = reverse_lazy('salon')

    def get_object(self, queryset=None):
        salon = Salon.objects.filter(owner=self.request.user).first()
        if not salon:
            # Create empty salon for the form
            salon = Salon(owner=self.request.user)
        return salon

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


# Service views
class ServiceListView(MasterRequiredMixin, ListView):
    """List master's services."""
    model = Service
    template_name = 'masters/service_list.html'
    context_object_name = 'services'

    def get_queryset(self):
        return Service.objects.filter(owner=self.request.user)


class ServiceCreateView(MasterRequiredMixin, CreateView):
    """Create service."""
    model = Service
    form_class = ServiceForm
    template_name = 'masters/service_form.html'
    success_url = reverse_lazy('service_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        # Get or create salon for the master
        salon = Salon.objects.filter(owner=self.request.user).first()
        if not salon:
            salon = Salon.objects.create(
                owner=self.request.user,
                name=f"Салон {self.request.user.master_profile.display_name}"
            )
        form.instance.salon = salon
        return super().form_valid(form)


class ServiceEditView(MasterRequiredMixin, UpdateView):
    """Edit service."""
    model = Service
    form_class = ServiceForm
    template_name = 'masters/service_form.html'
    success_url = reverse_lazy('service_list')

    def get_queryset(self):
        return Service.objects.filter(owner=self.request.user)


class ServiceDeleteView(MasterRequiredMixin, DeleteView):
    """Delete service."""
    model = Service
    template_name = 'masters/service_confirm_delete.html'
    success_url = reverse_lazy('service_list')

    def get_queryset(self):
        return Service.objects.filter(owner=self.request.user)
