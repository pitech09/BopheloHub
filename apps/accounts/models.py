from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
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

    def get_instructor_profile(self):
        """Return the related instructor profile if it exists."""
        try:
            return self.instructor_profile
        except ObjectDoesNotExist:
            return None

    def get_instructor_status(self):
        """Return the instructor verification status, or an empty string."""
        profile = self.get_instructor_profile()
        return profile.status if profile else ''
