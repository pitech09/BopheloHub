from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.conf import settings
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


class LessonNote(models.Model):
    """A student's personal notes for a specific lesson."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_notes')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='notes')
    content = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')
        verbose_name = 'Lesson Note'
        verbose_name_plural = 'Lesson Notes'

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"


class LessonComment(models.Model):
    """A comment/discussion on a specific lesson (supports threaded replies)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_comments')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='replies', blank=True, null=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Lesson Comment'
        verbose_name_plural = 'Lesson Comments'

    def __str__(self):
        return f"{self.user.username} on {self.lesson.title}"

    @property
    def is_reply(self):
        """Check if this comment is a reply to another comment."""
        return self.parent is not None


class LessonResource(models.Model):
    """Downloadable resources for a lesson (documents, PDFs, etc.)."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='lesson_resources/')
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='uploaded_resources')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = 'Lesson Resource'
        verbose_name_plural = 'Lesson Resources'

    def __str__(self):
        return f"{self.title} ({self.lesson.title})"

    def get_file_extension(self):
        """Get the file extension for display purposes."""
        import os
        return os.path.splitext(self.file.name)[1].lower().lstrip('.')
