from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import MasterProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_master_profile(sender, instance, created, **kwargs):
    """Create MasterProfile when a new master user is created."""
    if created and instance.role == 'MASTER':
        MasterProfile.objects.create(
            user=instance,
            display_name=instance.username or instance.email.split('@')[0]
        )
