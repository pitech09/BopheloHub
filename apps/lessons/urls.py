from django.urls import path
from .views import (
    LessonPlayerView,
    CompleteLessonView,
    QuizTakeView,
    QuizResultView,
    CurriculumView,
    SectionCreateView,
    SectionUpdateView,
    SectionDeleteView,
    LessonCreateView,
    LessonUpdateView,
    LessonDeleteView,
    ReorderLessonsView,
    ReorderSectionsView,
    QuizManageView,
    QuestionDeleteView,
)

urlpatterns = [
    # Student URLs
    path('lesson/<int:pk>/', LessonPlayerView.as_view(), name='lesson_play'),
    path('lesson/<int:pk>/complete/', CompleteLessonView.as_view(), name='lesson_complete'),
    path('quiz/<int:pk>/take/', QuizTakeView.as_view(), name='quiz_take'),
    path('quiz-result/<int:pk>/', QuizResultView.as_view(), name='quiz_result'),
    
    # Instructor URLs
    path('instructor/course/<int:pk>/curriculum/', CurriculumView.as_view(), name='curriculum'),
    path('instructor/course/<int:course_pk>/section/create/', SectionCreateView.as_view(), name='section_create'),
    path('instructor/section/<int:pk>/edit/', SectionUpdateView.as_view(), name='section_update'),
    path('instructor/section/<int:pk>/delete/', SectionDeleteView.as_view(), name='section_delete'),
    path('instructor/section/<int:section_pk>/lesson/create/', LessonCreateView.as_view(), name='lesson_create'),
    path('instructor/lesson/<int:pk>/edit/', LessonUpdateView.as_view(), name='lesson_update'),
    path('instructor/lesson/<int:pk>/delete/', LessonDeleteView.as_view(), name='lesson_delete'),
    path('instructor/lesson/<int:lesson_pk>/quiz/', QuizManageView.as_view(), name='quiz_manage'),
    path('instructor/question/<int:pk>/delete/', QuestionDeleteView.as_view(), name='question_delete'),
    
    # Reorder URLs (AJAX)
    path('instructor/section/<int:section_pk>/reorder/', ReorderLessonsView.as_view(), name='reorder_lessons'),
    path('instructor/course/<int:course_pk>/reorder-sections/', ReorderSectionsView.as_view(), name='reorder_sections'),
]
