from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import StudentRegistrationForm, InstructorRegistrationForm
from .models import User

class StudentRegisterView(CreateView):
    model = User
    form_class = StudentRegistrationForm
    template_name = 'accounts/register_student.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)   # auto-login after registration
        return redirect('profile')

class InstructorRegisterView(CreateView):
    model = User
    form_class = InstructorRegistrationForm
    template_name = 'accounts/register_instructor.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('instructor_apply')   # redirect to upload verification

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'