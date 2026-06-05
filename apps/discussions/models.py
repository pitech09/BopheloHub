from django.db import models
from accounts.models import User
from courses.models import Course


class Discussion(models.Model):
    """A discussion thread in a course forum."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='discussions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussions')
    title = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"[{self.course.title}] {self.title}"

    def reply_count(self):
        return self.replies.count()


class DiscussionReply(models.Model):
    """A reply to a discussion thread."""
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussion_replies')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_solution = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.user.username} on {self.discussion.title}"