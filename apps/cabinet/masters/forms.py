from django import forms
from .models import MasterProfile, Salon, Service


class MasterProfileForm(forms.ModelForm):
    """Form for editing master profile."""

    class Meta:
        model = MasterProfile
        fields = ['display_name', 'slug', 'phone', 'bio']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class SalonForm(forms.ModelForm):
    """Form for editing salon."""

    class Meta:
        model = Salon
        fields = ['name', 'address', 'description', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ServiceForm(forms.ModelForm):
    """Form for creating/editing service."""

    class Meta:
        model = Service
        fields = ['name', 'duration_min', 'price', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_min': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
