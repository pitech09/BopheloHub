from django.urls import path
from .views import (
    StudentDashboardView,
    CourseProgressView,
    CompleteEnrollmentView,
    EnrollWithPaymentView,
    ApproveEnrollmentView,
    RejectEnrollmentView,
    NotificationListView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
)

urlpatterns = [
    path('dashboard/', StudentDashboardView.as_view(), name='student_dashboard'),
    path('course/<slug:slug>/progress/', CourseProgressView.as_view(), name='course_progress'),
    path('complete/<int:pk>/', CompleteEnrollmentView.as_view(), name='complete_enrollment'),
    
    # Payment Enrollment
    path('course/<slug:slug>/enroll/', EnrollWithPaymentView.as_view(), name='enroll_course'),
    
    # Instructor approval/rejection
    path('enrollment/<int:pk>/approve/', ApproveEnrollmentView.as_view(), name='approve_enrollment'),
    path('enrollment/<int:pk>/reject/', RejectEnrollmentView.as_view(), name='reject_enrollment'),
    
    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notification/<int:pk>/mark-read/', NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
]