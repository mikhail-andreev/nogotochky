from django.db import models
from django.conf import settings
from django.utils.text import slugify


class MasterProfile(models.Model):
    """Master profile."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='master_profile'
    )
    display_name = models.CharField('Отображаемое имя', max_length=100)
    slug = models.SlugField('URL', unique=True, max_length=100)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    bio = models.TextField('О себе', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'master_profiles'
        verbose_name = 'Профиль мастера'
        verbose_name_plural = 'Профили мастеров'

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.display_name) or 'master'
        slug = base_slug
        counter = 1
        while MasterProfile.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug


class Salon(models.Model):
    """Salon/clinic card."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='salons',
        verbose_name='Владелец'
    )
    name = models.CharField('Название', max_length=200)
    address = models.CharField('Адрес', max_length=300, blank=True)
    description = models.TextField('Описание', blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'salons'
        verbose_name = 'Салон'
        verbose_name_plural = 'Салоны'

    def __str__(self):
        return self.name


class Service(models.Model):
    """Service offered by master."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name='Мастер'
    )
    salon = models.ForeignKey(
        Salon,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name='Салон'
    )
    name = models.CharField('Название', max_length=200)
    duration_min = models.PositiveIntegerField('Длительность (мин)')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активна', default=True)

    class Meta:
        db_table = 'services'
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

    def __str__(self):
        return f"{self.name} - {self.price} руб."
