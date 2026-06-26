from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg, Q, F, FloatField
from django.db.models.functions import Cast
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from .models import Enrollment, LessonCompletion
from courses.models import Course
from certificates.models import Certificate
from notifications.models import Notification
from payments.models import Payment
from payments.forms import PaymentUploadForm
from instructors.mixins import InstructorRequiredMixin


class StudentDashboardView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'enrollments/student_dashboard.html'
    context_object_name = 'enrollments'
    
    def get_queryset(self):
        return Enrollment.objects.filter(
            user=self.request.user
        ).select_related('course', 'course__instructor').order_by('-enrolled_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollments = self.get_queryset()
        
        # Stats
        context['completed_count'] = enrollments.filter(completed=True).count()
        context['in_progress_count'] = enrollments.filter(status='active', completed=False).count()
        context['pending_count'] = enrollments.filter(status='pending').count()
        context['certificates'] = Certificate.objects.filter(
            enrollment__user=self.request.user
        )
        
        # Learning stats
        context['streak_days'] = 0
        context['lessons_completed'] = LessonCompletion.objects.filter(
            enrollment__user=self.request.user
        ).count()
        context['total_hours'] = 0
        context['avg_quiz_score'] = 0
        
        # Weekly activity (mock data)
        context['weekly_activity'] = [
            {'day': 'Mon', 'minutes': 0},
            {'day': 'Tue', 'minutes': 0},
            {'day': 'Wed', 'minutes': 0},
            {'day': 'Thu', 'minutes': 0},
            {'day': 'Fri', 'minutes': 0},
            {'day': 'Sat', 'minutes': 0},
            {'day': 'Sun', 'minutes': 0},
        ]
        
        # Pending payments
        context['pending_payments'] = Payment.objects.filter(
            user=self.request.user, status='pending'
        ).select_related('course')
        
        return context


class CourseProgressView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'enrollments/course_progress.html'
    context_object_name = 'course'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        
        # Get user's enrollment
        enrollment = get_object_or_404(Enrollment, user=self.request.user, course=course)
        context['enrollment'] = enrollment
        
        # Get completed lessons
        completed_lessons = LessonCompletion.objects.filter(
            enrollment=enrollment
        ).values_list('lesson_id', flat=True)
        context['completed_lessons'] = list(completed_lessons)
        
        # Calculate progress
        total_lessons = sum(section.lessons.count() for section in course.sections.all())
        completed_count = len(completed_lessons)
        context['progress'] = (completed_count / total_lessons * 100) if total_lessons > 0 else 0
        
        return context


class CompleteEnrollmentView(LoginRequiredMixin, DetailView):
    model = Enrollment
    template_name = 'enrollments/enrollment_detail.html'
    
    def get(self, request, *args, **kwargs):
        enrollment = get_object_or_404(Enrollment, pk=self.kwargs['pk'], user=request.user)
        course = enrollment.course
        is_free_course = course.price == 0

        certificate = enrollment.complete_and_issue_certificate_if_eligible()
        if certificate:
            # Send notification
            Notification.objects.create(
                user=request.user,
                message=(
                    f'Congratulations! Your certificate for "{course.title}" is ready.'
                    if is_free_course
                    else f'Congratulations! You passed "{course.title}" with at least 70% and your certificate is ready.'
                )
            )
            
            return redirect('certificates:certificate_detail', pk=certificate.pk)

        if not is_free_course:
            if not enrollment.quizzes_ready():
                messages.warning(request, 'This course is not certificate-ready yet. The instructor must add quiz questions first.')
            elif not enrollment.passed_required_quizzes():
                messages.warning(request, 'Complete all lessons and pass every course quiz with at least 70% to receive your certificate.')
        
        return redirect('student_dashboard')


class EnrollWithPaymentView(LoginRequiredMixin, CreateView):
    """Handles enrollment with payment screenshot upload."""
    form_class = PaymentUploadForm
    template_name = 'enrollments/payment_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, slug=self.kwargs['slug'], is_published=True)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.course
        context['course'] = course
        context['total_lessons'] = sum(
            section.lessons.count() for section in course.sections.all()
        )
        context['enrolled_count'] = course.enrollments.count()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['course'] = self.course
        return kwargs

    def form_valid(self, form):
        # Check for existing enrollment
        enrollment, created = Enrollment.objects.get_or_create(
            user=self.request.user,
            course=self.course,
            defaults={'status': 'pending'}
        )

        # If enrollment already exists and is active, redirect
        if not created and enrollment.status == 'active':
            messages.info(self.request, 'You are already enrolled in this course.')
            return redirect('course_detail', slug=self.course.slug)

        # Save payment — NEVER trust the submitted amount
        payment = form.save(commit=False)
        payment.user = self.request.user
        payment.course = self.course
        payment.amount = self.course.price  # Server-authoritative price
        payment.status = 'pending'
        payment.save()

        # Update enrollment status to pending
        enrollment.status = 'pending'
        enrollment.save()

        # Notify instructor about new enrollment request with payment
        student_name = self.request.user.get_full_name() or self.request.user.username
        Notification.objects.create(
            user=self.course.instructor,
            message=f'{student_name} has submitted payment for "{self.course.title}". Reference: {payment.reference_number}',
        )

        # Notify student
        Notification.objects.create(
            user=self.request.user,
            message=f'Your payment for "{self.course.title}" has been submitted. Awaiting verification.',
        )

        messages.success(self.request, 'Payment submitted successfully! You will get access once verified.')
        return redirect('student_dashboard')


class ApproveEnrollmentView(LoginRequiredMixin, DetailView):
    """Instructor approves enrollment after payment verification."""
    
    def get(self, request, *args, **kwargs):
        enrollment = get_object_or_404(
            Enrollment, pk=self.kwargs['pk'], course__instructor=request.user
        )
        
        if enrollment.status == 'pending':
            enrollment.status = 'active'
            enrollment.save()
            
            # Update payment status
            payment = Payment.objects.filter(
                user=enrollment.user, course=enrollment.course, status='pending'
            ).first()
            if payment:
                payment.status = 'verified'
                payment.verified_by = request.user
                payment.verified_at = timezone.now()
                payment.save()
            
            # Notify student
            Notification.objects.create(
                user=enrollment.user,
                message=f'Your enrollment for "{enrollment.course.title}" has been approved! You can now access the course.',
            )
            
            messages.success(request, f'Enrollment for {enrollment.user.username} approved!')
        
        return redirect('instructor_dashboard')


class RejectEnrollmentView(LoginRequiredMixin, DetailView):
    """Instructor rejects enrollment."""
    
    def get(self, request, *args, **kwargs):
        enrollment = get_object_or_404(
            Enrollment, pk=self.kwargs['pk'], course__instructor=request.user
        )
        
        if enrollment.status == 'pending':
            enrollment.status = 'rejected'
            enrollment.save()
            
            # Update payment status
            payment = Payment.objects.filter(
                user=enrollment.user, course=enrollment.course, status='pending'
            ).first()
            if payment:
                payment.status = 'rejected'
                payment.save()
            
            # Notify student
            Notification.objects.create(
                user=enrollment.user,
                message=f'Your enrollment for "{enrollment.course.title}" has been rejected. Please contact support.',
            )
            
            messages.warning(request, f'Enrollment for {enrollment.user.username} rejected.')
        
        return redirect('instructor_dashboard')


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            user=self.request.user,
            is_read=False
        ).count()
        return context


class NotificationMarkReadView(LoginRequiredMixin, DetailView):
    model = Notification
    
    def get(self, request, *args, **kwargs):
        notification = get_object_or_404(Notification, pk=self.kwargs['pk'], user=request.user)
        notification.is_read = True
        notification.save()
        
        # Redirect back if provided, otherwise to notifications list
        next_url = request.GET.get('next', reverse_lazy('notifications'))
        return redirect(next_url)


class NotificationMarkAllReadView(LoginRequiredMixin, CreateView):
    def get(self, request, *args, **kwargs):
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return redirect('notifications')
