from django.db import models
from django.conf import settings
from courses.models import Course
from enrollments.models import Enrollment


class Assessment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assessments')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    total_points = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.course.title}"


class AssessmentQuestion(models.Model):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('essay', 'Essay'),
    ]

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='essay')
    points = models.PositiveIntegerField(default=10)
    order = models.PositiveIntegerField(default=0)

    # For multiple choice
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct_answer = models.CharField(max_length=1, blank=True, help_text="A, B, C, or D")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}"


class AssessmentSubmission(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='submissions')
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='assessment_submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded = models.BooleanField(default=False)
    score = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='graded_submissions'
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('assessment', 'enrollment')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.enrollment.user.username} - {self.assessment.title}"


class SubmissionAnswer(models.Model):
    submission = models.ForeignKey(AssessmentSubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(AssessmentQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    selected_option = models.CharField(max_length=1, blank=True)
    is_correct = models.BooleanField(null=True)
    points_earned = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Answer to Q{self.question.order}"