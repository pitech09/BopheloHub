from django.contrib import admin
from .models import Assessment, AssessmentQuestion, AssessmentSubmission, SubmissionAnswer


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'total_points', 'created_at']
    list_filter = ['course']


@admin.register(AssessmentQuestion)
class AssessmentQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'assessment', 'question_type', 'points', 'order']


@admin.register(AssessmentSubmission)
class AssessmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ['assessment', 'enrollment', 'graded', 'score', 'submitted_at']


@admin.register(SubmissionAnswer)
class SubmissionAnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'is_correct', 'points_earned']