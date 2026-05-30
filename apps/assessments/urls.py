from django.urls import path
from .views import (
    AssessmentListView,
    AssessmentCreateView,
    AssessmentDetailView,
    AssessmentUpdateView,
    AssessmentQuestionCreateView,
    AssessmentQuestionUpdateView,
    AssessmentQuestionDeleteView,
    AssessmentTakeView,
    AssessmentGradeView,
)

urlpatterns = [
    # Instructor assessment management
    path('course/<int:course_id>/assessments/', AssessmentListView.as_view(), name='assessment_list'),
    path('course/<int:course_id>/assessments/create/', AssessmentCreateView.as_view(), name='assessment_create'),
    path('assessments/<int:pk>/', AssessmentDetailView.as_view(), name='assessment_detail'),
    path('assessments/<int:pk>/edit/', AssessmentUpdateView.as_view(), name='assessment_edit'),
    
    # Questions
    path('assessments/<int:pk>/questions/add/', AssessmentQuestionCreateView.as_view(), name='assessment_question_add'),
    path('assessments/questions/<int:pk>/edit/', AssessmentQuestionUpdateView.as_view(), name='assessment_question_edit'),
    path('assessments/questions/<int:pk>/delete/', AssessmentQuestionDeleteView.as_view(), name='assessment_question_delete'),
    
    # Student taking assessment
    path('assessments/<int:pk>/take/', AssessmentTakeView.as_view(), name='assessment_take'),
    
    # Instructor grading
    path('assessments/submissions/<int:pk>/grade/', AssessmentGradeView.as_view(), name='assessment_grade'),
]