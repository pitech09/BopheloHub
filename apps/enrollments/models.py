from django.db import models
from accounts.models import User
from courses.models import Course
from lessons.models import Lesson


class Enrollment(models.Model):
    ENROLLMENT_STATUS = [
        ('pending', 'Pending Payment Verification'),
        ('active', 'Active'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS, default='pending')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    last_accessed = models.DateTimeField(null=True, blank=True)
    progress = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.user.username} in {self.course.title}"

    def calculate_progress(self):
        """Calculate and update progress percentage."""
        total_lessons = sum(section.lessons.count() for section in self.course.sections.all())
        if total_lessons == 0:
            self.progress = 0
            return 0
        
        completed_lessons = self.lesson_completions.count()
        self.progress = (completed_lessons / total_lessons) * 100
        self.save()
        return self.progress


class LessonCompletion(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_completions')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('enrollment', 'lesson')
    
    def __str__(self):
        return f"{self.enrollment.user.username} - {self.lesson.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update enrollment progress
        self.enrollment.calculate_progress()
        # Update last accessed
        self.enrollment.last_accessed = self.completed_at
        self.enrollment.save()