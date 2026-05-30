from django.db import models
from accounts.models import User

class InstructorProfile(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    headline = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    id_document = models.FileField(upload_to='verification/ids/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    qualifications = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Instructor: {self.user.email}"