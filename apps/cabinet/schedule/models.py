from django.db import models
from django.conf import settings


class ScheduleSlot(models.Model):
    """Schedule slot for booking."""

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Доступен'
        BOOKED = 'BOOKED', 'Забронирован'
        BLOCKED = 'BLOCKED', 'Заблокирован'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='schedule_slots',
        verbose_name='Мастер'
    )
    start_at = models.DateTimeField('Начало')
    end_at = models.DateTimeField('Конец')
    status = models.CharField(
        'Статус',
        max_length=10,
        choices=Status.choices,
        default=Status.AVAILABLE
    )

    class Meta:
        db_table = 'schedule_slots'
        verbose_name = 'Слот расписания'
        verbose_name_plural = 'Слоты расписания'
        ordering = ['start_at']

    def __str__(self):
        return f"{self.start_at.strftime('%d.%m.%Y %H:%M')} - {self.end_at.strftime('%H:%M')}"

    @property
    def duration_minutes(self):
        """Return slot duration in minutes."""
        return int((self.end_at - self.start_at).total_seconds() / 60)

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE


class Booking(models.Model):
    """Client booking."""

    class Status(models.TextChoices):
        CREATED = 'CREATED', 'Создана'
        CANCELLED = 'CANCELLED', 'Отменена'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Мастер'
    )
    service = models.ForeignKey(
        'masters.Service',
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Услуга'
    )
    slot = models.OneToOneField(
        ScheduleSlot,
        on_delete=models.CASCADE,
        related_name='booking',
        verbose_name='Начальный слот'
    )
    booked_slots = models.ManyToManyField(
        ScheduleSlot,
        related_name='bookings_all',
        verbose_name='Все забронированные слоты',
        blank=True
    )
    client_name = models.CharField('Имя клиента', max_length=100)
    client_phone = models.CharField('Телефон клиента', max_length=20)
    notes = models.TextField('Комментарий', blank=True)
    status = models.CharField(
        'Статус',
        max_length=10,
        choices=Status.choices,
        default=Status.CREATED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bookings'
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client_name} - {self.service.name} ({self.slot.start_at.strftime('%d.%m.%Y %H:%M')})"

    def cancel(self):
        """Cancel booking and free all booked slots."""
        self.status = self.Status.CANCELLED
        self.booked_slots.update(status=ScheduleSlot.Status.AVAILABLE)
        self.save()
