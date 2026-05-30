from django.db import models
from enrollments.models import Enrollment

class Certificate(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name='certificate')
    issued_at = models.DateTimeField(auto_now_add=True)
    certificate_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"Certificate for {self.enrollment.user.username}"