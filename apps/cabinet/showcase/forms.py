from django import forms


class PublicBookingForm(forms.Form):
    """Booking form for visitors."""
    service_id = forms.IntegerField(widget=forms.HiddenInput())
    slot_id = forms.IntegerField(widget=forms.HiddenInput())
    client_name = forms.CharField(
        label='Ваше имя',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'})
    )
    client_phone = forms.CharField(
        label='Телефон',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (___) ___-__-__'})
    )
    notes = forms.CharField(
        label='Комментарий',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Дополнительная информация'})
    )
