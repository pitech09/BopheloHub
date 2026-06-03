from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .forms import StudentRegistrationForm, InstructorRegistrationForm, ProfileEditForm
from .models import User
from enrollments.models import Enrollment
from certificates.models import Certificate
from reviews.models import Review

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

    def get_success_url(self):
        if self.request.user.is_superuser:
            return reverse('owner_dashboard')
        return reverse('profile')

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Enrollments
        enrollments = Enrollment.objects.filter(user=user).select_related('course')

        # Certificates
        certificates = Certificate.objects.filter(enrollment__user=user).select_related('enrollment__course')

        # Reviews written by the user
        reviews = Review.objects.filter(user=user).select_related('course')

        # Stats
        active_enrollments = enrollments.filter(status='active').count()
        completed_courses = enrollments.filter(completed=True).count()
        total_certificates = certificates.count()

        # Profile edit form
        form = ProfileEditForm(instance=user)

        context.update({
            'enrollments': enrollments,
            'certificates': certificates,
            'reviews': reviews,
            'active_enrollments': active_enrollments,
            'completed_courses': completed_courses,
            'total_certificates': total_certificates,
            'form': form,
        })
        return context

    def post(self, request, *args, **kwargs):
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
        # Re-render with errors
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)
