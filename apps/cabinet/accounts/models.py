from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role field."""

    class Role(models.TextChoices):
        MASTER = 'MASTER', 'Мастер'
        ADMIN = 'ADMIN', 'Администратор'

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MASTER
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email

    @property
    def is_master(self):
        return self.role == self.Role.MASTER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN
