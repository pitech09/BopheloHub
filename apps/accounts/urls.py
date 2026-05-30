from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    StudentRegisterView, InstructorRegisterView,
    CustomLoginView, ProfileView
)
from instructors.views import InstructorApplicationView

urlpatterns = [
    path('register/student/', StudentRegisterView.as_view(), name='register_student'),
    path('register/instructor/', InstructorRegisterView.as_view(), name='register_instructor'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('instructor/apply/', InstructorApplicationView.as_view(), name='instructor_apply'),
]