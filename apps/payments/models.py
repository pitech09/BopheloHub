from django.db import models
from django.conf import settings
from courses.models import Course


class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    reference_number = models.CharField(max_length=100, unique=True)
    screenshot = models.ImageField(upload_to='payments/screenshots/')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    admin_note = models.TextField(blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='payments_verified'
    )

    class Meta:
        ordering = ['-paid_at']

    def __str__(self):
        return f"Payment {self.reference_number} - {self.user.username} - {self.course.title}"