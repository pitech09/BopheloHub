from django.urls import path
from .views import (
    OwnerDashboardView,
    ApproveInstructorView,
    RejectInstructorView,
    OwnerPaymentListView,
    OwnerPaymentVerifyView,
    OwnerPaymentRejectView,
    OwnerUserListView,
    OwnerUserDetailView,
    OwnerUserToggleActiveView,
    OwnerCourseListView,
    OwnerCourseDeleteView,
    OwnerEnrollmentListView,
    OwnerEnrollmentApproveView,
    OwnerEnrollmentRejectView,
    OwnerInstructorListView,
    OwnerSystemHealthView,
)

urlpatterns = [
    # Dashboard
    path('owner/', OwnerDashboardView.as_view(), name='owner_dashboard'),

    # Instructor Approvals
    path('owner/instructors/<int:pk>/approve/', ApproveInstructorView.as_view(), name='approve_instructor'),
    path('owner/instructors/<int:pk>/reject/', RejectInstructorView.as_view(), name='reject_instructor'),

    # Payment Management
    path('owner/payments/', OwnerPaymentListView.as_view(), name='owner_payment_list'),
    path('owner/payments/<int:pk>/verify/', OwnerPaymentVerifyView.as_view(), name='owner_payment_verify'),
    path('owner/payments/<int:pk>/reject/', OwnerPaymentRejectView.as_view(), name='owner_payment_reject'),

    # User Management
    path('owner/users/', OwnerUserListView.as_view(), name='owner_user_list'),
    path('owner/users/<int:pk>/', OwnerUserDetailView.as_view(), name='owner_user_detail'),
    path('owner/users/<int:pk>/toggle-active/', OwnerUserToggleActiveView.as_view(), name='owner_user_toggle_active'),

    # Course Management
    path('owner/courses/', OwnerCourseListView.as_view(), name='owner_course_list'),
    path('owner/courses/<int:pk>/delete/', OwnerCourseDeleteView.as_view(), name='owner_course_delete'),

    # Enrollment Management
    path('owner/enrollments/', OwnerEnrollmentListView.as_view(), name='owner_enrollment_list'),
    path('owner/enrollments/<int:pk>/approve/', OwnerEnrollmentApproveView.as_view(), name='owner_enrollment_approve'),
    path('owner/enrollments/<int:pk>/reject/', OwnerEnrollmentRejectView.as_view(), name='owner_enrollment_reject'),

    # Instructor Management
    path('owner/instructors/', OwnerInstructorListView.as_view(), name='owner_instructor_list'),

    # System Health
    path('owner/system-health/', OwnerSystemHealthView.as_view(), name='owner_system_health'),
]
