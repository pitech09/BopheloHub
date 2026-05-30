from django.urls import path
from .views import (
    HomeView,
    CourseDetailView, 
    CourseListView, 
    InstructorDashboardView, 
    CourseCreateView, 
    CourseUpdateView,
    EnrollCourseView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),          # homepage
    path('courses/', CourseListView.as_view(), name='course_list'),          # course listing with search/filter
    path('course/<slug:slug>/', CourseDetailView.as_view(), name='course_detail'),
    path('course/<slug:slug>/enroll/', EnrollCourseView.as_view(), name='enroll_course'),
    path('instructor/', InstructorDashboardView.as_view(), name='instructor_dashboard'),
    path('instructor/course/create/', CourseCreateView.as_view(), name='course_create'),
    path('instructor/course/<int:pk>/edit/', CourseUpdateView.as_view(), name='course_edit'),
]