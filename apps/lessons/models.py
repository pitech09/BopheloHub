from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from courses.models import Course

class Section(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('course', 'order')

    def __str__(self):
        return f"{self.course.title} → {self.title}"

class Lesson(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField()
    content = CKEditor5Field(config_name='extends')   # CKEditor 5
    video_url = models.URLField(blank=True, help_text="YouTube or Vimeo embed URL")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ('section', 'order')

    def __str__(self):
        return f"{self.section.course.title} – {self.title}"