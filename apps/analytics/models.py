from django.db import models
from accounts.models import User
from courses.models import Course

class CourseView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # null for anonymous
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

class LessonView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    lesson = models.ForeignKey('lessons.Lesson', on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)