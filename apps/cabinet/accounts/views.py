from django.contrib.auth import login
from django.contrib.auth.views import LoginView as BaseLoginView, LogoutView as BaseLogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import UserRegistrationForm


class RegisterView(CreateView):
    """Master registration view."""
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class LoginView(BaseLoginView):
    """Login view."""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class LogoutView(BaseLogoutView):
    """Logout view."""
    next_page = reverse_lazy('login')
