from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify

class User(AbstractUser):
    email = models.EmailField(unique=True)          # override to make unique
    is_instructor = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']          # still required for createsuperuser; we auto-generate in forms

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.username:
            # auto-generate from email (fallback to a random string)
            base = self.email.split('@')[0]
            self.username = slugify(base)[:150] or f"user_{self.pk}"
        super().save(*args, **kwargs)