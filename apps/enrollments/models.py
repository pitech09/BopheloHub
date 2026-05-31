from django.db import models
import uuid
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

    def course_quizzes(self):
        from quizzes.models import Quiz
        return Quiz.objects.filter(lesson__section__course=self.course).prefetch_related('questions')

    def total_lessons_count(self):
        return sum(section.lessons.count() for section in self.course.sections.all())

    def completed_lessons_count(self):
        return self.lesson_completions.count()

    def lessons_complete(self):
        total_lessons = self.total_lessons_count()
        return total_lessons > 0 and self.completed_lessons_count() >= total_lessons

    def quizzes_ready(self):
        quizzes = list(self.course_quizzes())
        return bool(quizzes) and all(quiz.questions.exists() for quiz in quizzes)

    def passed_required_quizzes(self):
        from quizzes.models import UserQuizAttempt
        quizzes = list(self.course_quizzes())
        if not quizzes or not self.quizzes_ready():
            return False

        for quiz in quizzes:
            passed = UserQuizAttempt.objects.filter(
                user=self.user,
                quiz=quiz,
                passed=True,
                score__gte=quiz.pass_percentage,
            ).exists()
            if not passed:
                return False
        return True

    def course_quiz_score(self):
        from quizzes.models import UserQuizAttempt
        quizzes = list(self.course_quizzes())
        if not quizzes:
            return 0

        best_scores = []
        for quiz in quizzes:
            best_attempt = UserQuizAttempt.objects.filter(
                user=self.user,
                quiz=quiz,
            ).order_by('-score').first()
            best_scores.append(best_attempt.score if best_attempt else 0)

        return sum(best_scores) / len(best_scores)

    def can_receive_certificate(self):
        return (
            self.status == 'active'
            and self.lessons_complete()
            and self.quizzes_ready()
            and self.passed_required_quizzes()
            and self.course_quiz_score() >= 70
        )

    def complete_and_issue_certificate_if_eligible(self):
        if not self.can_receive_certificate():
            return None

        self.completed = True
        self.save(update_fields=['completed'])

        from certificates.models import Certificate
        certificate, _ = Certificate.objects.get_or_create(
            enrollment=self,
            defaults={
                'certificate_code': str(uuid.uuid4()).replace('-', '').upper()[:16]
            },
        )
        return certificate


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
