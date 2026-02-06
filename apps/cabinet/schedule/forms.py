from django import forms
from datetime import datetime, timedelta


class SlotCreateForm(forms.Form):
    """Form for generating schedule slots."""
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    start_time = forms.TimeField(
        label='Время начала',
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'})
    )
    end_time = forms.TimeField(
        label='Время окончания',
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'})
    )
    slot_duration = forms.IntegerField(
        label='Длительность слота (мин)',
        initial=30,
        min_value=15,
        max_value=480,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('Время начала должно быть раньше времени окончания')

        return cleaned_data

    def generate_slots(self, owner):
        """Generate slots based on form data."""
        from .models import ScheduleSlot
        from django.utils import timezone

        date = self.cleaned_data['date']
        start_time = self.cleaned_data['start_time']
        end_time = self.cleaned_data['end_time']
        duration = self.cleaned_data['slot_duration']

        slots = []
        current_start = datetime.combine(date, start_time)
        day_end = datetime.combine(date, end_time)

        # Make timezone-aware
        current_start = timezone.make_aware(current_start)
        day_end = timezone.make_aware(day_end)

        while current_start + timedelta(minutes=duration) <= day_end:
            current_end = current_start + timedelta(minutes=duration)
            slot = ScheduleSlot(
                owner=owner,
                start_at=current_start,
                end_at=current_end,
                status=ScheduleSlot.Status.AVAILABLE
            )
            slots.append(slot)
            current_start = current_end

        ScheduleSlot.objects.bulk_create(slots)
        return len(slots)
