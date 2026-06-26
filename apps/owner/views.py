from decimal import Decimal
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.views.generic import TemplateView, DetailView, ListView, View
from django.db.models import Sum, Count, Q, Avg
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse_lazy

from accounts.models import User
from courses.models import Course, Category
from enrollments.models import Enrollment
from payments.models import Payment
from instructors.models import InstructorProfile
from reviews.models import Review
from assessments.models import Assessment, AssessmentSubmission
from certificates.models import Certificate
from lessons.models import Lesson, Section
from quizzes.models import Quiz, UserQuizAttempt


class OwnerRequiredMixin(UserPassesTestMixin):
    """Only allow superusers (platform owners) to access."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, 'You do not have permission to access the platform dashboard.')
        return redirect('home')


class OwnerDashboardView(OwnerRequiredMixin, TemplateView):
    template_name = 'owner/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        now = timezone.now()

        # --- Financial Data ---
        verified_payments = Payment.objects.filter(status='verified')
        pending_payments = Payment.objects.filter(status='pending')

        total_revenue = verified_payments.aggregate(Sum('amount'))['amount__sum'] or 0
        platform_fee = total_revenue * Decimal('0.15')
        instructor_payouts = total_revenue * Decimal('0.85')
        total_payments = verified_payments.count()
        pending_revenue = pending_payments.aggregate(Sum('amount'))['amount__sum'] or 0
        pending_payments_count = pending_payments.count()

        context['total_revenue'] = total_revenue
        context['platform_fee'] = platform_fee
        context['instructor_payouts'] = instructor_payouts
        context['total_payments'] = total_payments
        context['pending_revenue'] = pending_revenue
        context['pending_payments_count'] = pending_payments_count

        # --- Monthly Breakdown (last 6 months) ---
        months = []
        for i in range(5, -1, -1):
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timezone.timedelta(days=30 * i)
            month_start = month_start.replace(day=1)
            if i > 0:
                month_end = month_start + timezone.timedelta(days=32)
                month_end = month_end.replace(day=1)
            else:
                month_end = now

            month_payments = verified_payments.filter(
                verified_at__gte=month_start,
                verified_at__lt=month_end
            )
            month_revenue = month_payments.aggregate(Sum('amount'))['amount__sum'] or 0
            month_count = month_payments.count()

            months.append({
                'label': month_start.strftime('%b %Y'),
                'revenue': month_revenue,
                'count': month_count,
                'fee': month_revenue * Decimal('0.15'),
            })

        context['monthly_data'] = months

        # --- Pending Instructor Requests ---
        context['pending_instructors'] = InstructorProfile.objects.filter(
            status='pending'
        ).select_related('user').order_by('-user__date_joined')[:20]

        # --- Total Instructor Requests Count ---
        context['pending_instructor_count'] = InstructorProfile.objects.filter(status='pending').count()

        # --- Platform Metrics ---
        total_users = User.objects.count()
        total_students = User.objects.filter(is_instructor=False, is_superuser=False).count()
        total_instructors = User.objects.filter(
            is_instructor=True,
            instructor_profile__status='verified'
        ).count()
        total_courses = Course.objects.count()
        published_courses = Course.objects.filter(is_published=True).count()
        draft_courses = Course.objects.filter(is_published=False).count()
        total_enrollments = Enrollment.objects.count()
        active_enrollments = Enrollment.objects.filter(status='active').count()
        pending_enrollments = Enrollment.objects.filter(status='pending').count()
        total_reviews = Review.objects.count()
        total_certificates = Certificate.objects.count()
        total_assessments = Assessment.objects.count()
        pending_submissions = AssessmentSubmission.objects.filter(graded=False).count()
        total_categories = Category.objects.count()
        total_lessons = Lesson.objects.count()
        total_quiz_attempts = UserQuizAttempt.objects.count()

        context['total_users'] = total_users
        context['total_students'] = total_students
        context['total_instructors'] = total_instructors
        context['total_courses'] = total_courses
        context['published_courses'] = published_courses
        context['draft_courses'] = draft_courses
        context['total_enrollments'] = total_enrollments
        context['active_enrollments'] = active_enrollments
        context['pending_enrollments'] = pending_enrollments
        context['total_reviews'] = total_reviews
        context['total_certificates'] = total_certificates
        context['total_assessments'] = total_assessments
        context['pending_submissions'] = pending_submissions
        context['total_categories'] = total_categories
        context['total_lessons'] = total_lessons
        context['total_quiz_attempts'] = total_quiz_attempts

        # --- Average Rating ---
        avg_rating = Review.objects.aggregate(Avg('rating'))['rating__avg']
        context['avg_rating'] = round(avg_rating, 1) if avg_rating else 0

        # --- Top Courses by Revenue ---
        top_courses = Course.objects.filter(
            is_published=True,
            payments__status='verified'
        ).annotate(
            enrolled_count=Count('enrollments', filter=Q(enrollments__status='active')),
            revenue=Sum('payments__amount', filter=Q(payments__status='verified'))
        ).filter(revenue__gt=0).order_by('-revenue')[:10]

        for c in top_courses:
            c.fee = (c.revenue or Decimal('0')) * Decimal('0.15')

        context['top_courses'] = top_courses

        # --- Top Rated Courses ---
        top_rated = Course.objects.filter(
            is_published=True,
            reviews__isnull=False
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).filter(review_count__gt=0).order_by('-avg_rating')[:5]

        context['top_rated_courses'] = top_rated

        # --- Most Enrolled Courses ---
        most_enrolled = Course.objects.filter(
            is_published=True
        ).annotate(
            enrolled_count=Count('enrollments', filter=Q(enrollments__status='active')),
        ).filter(enrolled_count__gt=0).order_by('-enrolled_count')[:5]

        context['most_enrolled_courses'] = most_enrolled

        # --- Recent Activity ---
        context['recent_users'] = User.objects.order_by('-date_joined')[:5]
        context['recent_courses'] = Course.objects.order_by('-created_at')[:5]
        context['recent_enrollments'] = Enrollment.objects.select_related(
            'user', 'course'
        ).order_by('-enrolled_at')[:5]
        context['recent_payments'] = Payment.objects.select_related(
            'user', 'course'
        ).order_by('-paid_at')[:10]
        context['recent_reviews'] = Review.objects.select_related(
            'user', 'course'
        ).order_by('-created_at')[:5]

        # --- Revenue by Category ---
        category_revenue = []
        for cat in Category.objects.all():
            cat_rev = Payment.objects.filter(
                status='verified',
                course__category=cat
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            if cat_rev > 0:
                category_revenue.append({
                    'name': cat.name,
                    'revenue': cat_rev,
                })
        category_revenue.sort(key=lambda x: x['revenue'], reverse=True)
        context['category_revenue'] = category_revenue

        # --- Growth Metrics (vs last month) ---
        last_month = now - timezone.timedelta(days=30)
        prev_users = User.objects.filter(date_joined__lt=last_month).count()
        prev_courses = Course.objects.filter(created_at__lt=last_month).count()
        new_users = total_users - prev_users
        new_courses = total_courses - prev_courses

        context['new_users_this_month'] = max(new_users, 0)
        context['new_courses_this_month'] = max(new_courses, 0)
        context['user_growth_pct'] = round((new_users / prev_users * 100), 1) if prev_users > 0 else 100
        context['course_growth_pct'] = round((new_courses / prev_courses * 100), 1) if prev_courses > 0 else 100

        return context


# ==================== Instructor Approvals (Original) ====================

class ApproveInstructorView(OwnerRequiredMixin, DetailView):
    model = InstructorProfile

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(InstructorProfile, pk=self.kwargs['pk'], status='pending')
        profile.status = 'verified'
        profile.save()

        # Mark the user as instructor
        user = profile.user
        user.is_instructor = True
        user.save()

        name = user.get_full_name() or user.username

        # Notify
        from notifications.models import Notification
        Notification.objects.create(
            user=user,
            message='Congratulations! Your instructor application has been approved. You can now create and publish courses.',
        )

        messages.success(request, f'{name} has been approved as an instructor.')
        return redirect(self.request.META.get('HTTP_REFERER', 'owner_instructor_list'))


class RejectInstructorView(OwnerRequiredMixin, DetailView):
    model = InstructorProfile

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(InstructorProfile, pk=self.kwargs['pk'], status='pending')
        profile.status = 'rejected'
        profile.save()

        name = profile.user.get_full_name() or profile.user.username

        from notifications.models import Notification
        Notification.objects.create(
            user=profile.user,
            message='Your instructor application has been rejected. Please contact support for more information.',
        )

        messages.warning(request, f'Instructor application for {name} has been rejected.')
        return redirect(self.request.META.get('HTTP_REFERER', 'owner_instructor_list'))


# ==================== Payment Management ====================

class OwnerPaymentListView(OwnerRequiredMixin, ListView):
    model = Payment
    template_name = 'owner/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 50

    def get_queryset(self):
        qs = Payment.objects.select_related('user', 'course', 'verified_by').order_by('-paid_at')

        status = self.request.GET.get('status')
        if status in ('pending', 'verified', 'rejected'):
            qs = qs.filter(status=status)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(reference_number__icontains=q) |
                Q(user__email__icontains=q) |
                Q(user__username__icontains=q) |
                Q(course__title__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['pending_count'] = Payment.objects.filter(status='pending').count()
        context['verified_count'] = Payment.objects.filter(status='verified').count()
        context['rejected_count'] = Payment.objects.filter(status='rejected').count()
        context['total_count'] = Payment.objects.count()
        return context


class OwnerPaymentVerifyView(OwnerRequiredMixin, DetailView):
    model = Payment

    def get(self, request, *args, **kwargs):
        payment = get_object_or_404(Payment, pk=self.kwargs['pk'], status='pending')
        payment.status = 'verified'
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.save()

        # Activate enrollment if exists
        enrollment = Enrollment.objects.filter(
            user=payment.user, course=payment.course, status='pending'
        ).first()
        if enrollment:
            enrollment.status = 'active'
            enrollment.save()

        from notifications.models import Notification
        Notification.objects.create(
            user=payment.user,
            message=f'Your payment of M{payment.amount} for "{payment.course.title}" has been verified! You now have full access.',
        )

        messages.success(request, f'Payment {payment.reference_number} verified successfully.')
        return redirect(self.request.META.get('HTTP_REFERER', 'owner_payment_list'))


class OwnerPaymentRejectView(OwnerRequiredMixin, DetailView):
    model = Payment

    def get(self, request, *args, **kwargs):
        payment = get_object_or_404(Payment, pk=self.kwargs['pk'], status='pending')
        payment.status = 'rejected'
        payment.save()

        # Reject enrollment if exists
        enrollment = Enrollment.objects.filter(
            user=payment.user, course=payment.course, status='pending'
        ).first()
        if enrollment:
            enrollment.status = 'rejected'
            enrollment.save()

        from notifications.models import Notification
        Notification.objects.create(
            user=payment.user,
            message=f'Your payment of M{payment.amount} for "{payment.course.title}" has been rejected. Please contact support or upload a new payment.',
        )

        messages.warning(request, f'Payment {payment.reference_number} rejected.')
        return redirect(self.request.META.get('HTTP_REFERER', 'owner_payment_list'))


# ==================== User Management ====================

class OwnerUserListView(OwnerRequiredMixin, ListView):
    model = User
    template_name = 'owner/user_list.html'
    context_object_name = 'users'
    paginate_by = 50

    def get_queryset(self):
        qs = User.objects.all().order_by('-date_joined')

        role = self.request.GET.get('role')
        if role == 'instructor':
            qs = qs.filter(is_instructor=True)
        elif role == 'student':
            qs = qs.filter(is_instructor=False, is_superuser=False)
        elif role == 'admin':
            qs = qs.filter(is_superuser=True)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(email__icontains=q) |
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_role'] = self.request.GET.get('role', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['total_users_count'] = User.objects.count()
        context['instructor_count'] = User.objects.filter(is_instructor=True).count()
        context['student_count'] = User.objects.filter(is_instructor=False, is_superuser=False).count()
        context['admin_count'] = User.objects.filter(is_superuser=True).count()
        return context


class OwnerUserDetailView(OwnerRequiredMixin, DetailView):
    model = User
    template_name = 'owner/user_detail.html'
    context_object_name = 'user_obj'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        context['enrollments'] = Enrollment.objects.filter(user=user).select_related('course')
        context['payments'] = Payment.objects.filter(user=user).select_related('course')
        context['reviews'] = Review.objects.filter(user=user).select_related('course')
        if hasattr(user, 'instructor_profile'):
            context['instructor_profile'] = user.instructor_profile
        return context


class OwnerUserToggleActiveView(OwnerRequiredMixin, DetailView):
    model = User

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        if user.is_superuser:
            messages.error(request, 'Cannot deactivate superusers.')
        else:
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'{user.email} has been {status}.')
        return redirect('owner_user_list')


# ==================== Course Management ====================

class OwnerCourseListView(OwnerRequiredMixin, ListView):
    model = Course
    template_name = 'owner/course_list.html'
    context_object_name = 'courses'
    paginate_by = 50

    def get_queryset(self):
        qs = Course.objects.select_related('instructor', 'category').annotate(
            enrolled_count=Count('enrollments', filter=Q(enrollments__status='active')),
            review_count=Count('reviews'),
            avg_rating=Avg('reviews__rating'),
        ).order_by('-created_at')

        status = self.request.GET.get('status')
        if status == 'published':
            qs = qs.filter(is_published=True)
        elif status == 'draft':
            qs = qs.filter(is_published=False)

        cat = self.request.GET.get('category')
        if cat:
            qs = qs.filter(category__slug=cat)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(instructor__email__icontains=q) |
                Q(instructor__username__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['categories'] = Category.objects.all()
        context['published_count'] = Course.objects.filter(is_published=True).count()
        context['draft_count'] = Course.objects.filter(is_published=False).count()
        context['total_courses_count'] = Course.objects.count()
        return context


class OwnerCourseDeleteView(OwnerRequiredMixin, DetailView):
    model = Course

    def post(self, request, *args, **kwargs):
        course = self.get_object()
        title = course.title
        course.delete()
        messages.success(request, f'Course "{title}" has been deleted.')
        return redirect('owner_course_list')


# ==================== Enrollment Management ====================

class OwnerEnrollmentListView(OwnerRequiredMixin, ListView):
    model = Enrollment
    template_name = 'owner/enrollment_list.html'
    context_object_name = 'enrollments'
    paginate_by = 50

    def get_queryset(self):
        qs = Enrollment.objects.select_related('user', 'course').order_by('-enrolled_at')

        status = self.request.GET.get('status')
        if status in ('pending', 'active', 'rejected'):
            qs = qs.filter(status=status)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(user__email__icontains=q) |
                Q(user__username__icontains=q) |
                Q(course__title__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['pending_count'] = Enrollment.objects.filter(status='pending').count()
        context['active_count'] = Enrollment.objects.filter(status='active').count()
        context['rejected_count'] = Enrollment.objects.filter(status='rejected').count()
        context['total_count'] = Enrollment.objects.count()
        return context


class OwnerEnrollmentApproveView(OwnerRequiredMixin, DetailView):
    model = Enrollment

    def get(self, request, *args, **kwargs):
        enrollment = get_object_or_404(Enrollment, pk=self.kwargs['pk'], status='pending')
        enrollment.status = 'active'
        enrollment.save()

        from notifications.models import Notification
        Notification.objects.create(
            user=enrollment.user,
            message=f'Your enrollment for "{enrollment.course.title}" has been approved by the platform admin.',
        )
        messages.success(request, f'Enrollment for {enrollment.user.username} approved.')
        return redirect(self.request.META.get('HTTP_REFERER', 'owner_enrollment_list'))


class OwnerEnrollmentRejectView(OwnerRequiredMixin, DetailView):
    model = Enrollment

    def get(self, request, *args, **kwargs):
        enrollment = get_object_or_404(Enrollment, pk=self.kwargs['pk'], status='pending')
        enrollment.status = 'rejected'
        enrollment.save()

        from notifications.models import Notification
        Notification.objects.create(
            user=enrollment.user,
            message=f'Your enrollment for "{enrollment.course.title}" has been rejected by the platform admin.',
        )
        messages.warning(request, f'Enrollment for {enrollment.user.username} rejected.')
        return redirect(self.request.META.get('HTTP_REFERER', 'owner_enrollment_list'))


# ==================== Instructor Management ====================

class OwnerInstructorListView(OwnerRequiredMixin, ListView):
    model = InstructorProfile
    template_name = 'owner/instructor_list.html'
    context_object_name = 'profiles'
    paginate_by = 50

    def get_queryset(self):
        qs = InstructorProfile.objects.select_related('user').order_by('-user__date_joined')

        status = self.request.GET.get('status')
        if status in ('pending', 'verified', 'rejected'):
            qs = qs.filter(status=status)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(user__email__icontains=q) |
                Q(user__username__icontains=q) |
                Q(headline__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['pending_count'] = InstructorProfile.objects.filter(status='pending').count()
        context['verified_count'] = InstructorProfile.objects.filter(status='verified').count()
        context['rejected_count'] = InstructorProfile.objects.filter(status='rejected').count()
        context['total_count'] = InstructorProfile.objects.count()
        return context


class OwnerInstructorDetailView(OwnerRequiredMixin, DetailView):
    model = InstructorProfile
    template_name = 'owner/instructor_detail.html'
    context_object_name = 'profile'

    def get_queryset(self):
        return InstructorProfile.objects.select_related('user').order_by('-user__date_joined')


# ==================== System Data Export / Summary ====================

class OwnerSystemHealthView(OwnerRequiredMixin, TemplateView):
    template_name = 'owner/system_health.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['user_count'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['course_count'] = Course.objects.count()
        context['enrollment_count'] = Enrollment.objects.count()
        context['payment_count'] = Payment.objects.count()
        context['review_count'] = Review.objects.count()
        context['lesson_count'] = Lesson.objects.count()
        context['section_count'] = Section.objects.count()
        context['certificate_count'] = Certificate.objects.count()
        context['assessment_count'] = Assessment.objects.count()
        context['submission_count'] = AssessmentSubmission.objects.count()
        context['quiz_count'] = Quiz.objects.count()
        context['quiz_attempt_count'] = UserQuizAttempt.objects.count()
        context['category_count'] = Category.objects.count()

        # Courses without any lessons
        context['empty_courses'] = Course.objects.filter(sections__isnull=True).count()
        # Users with no enrollments
        context['inactive_users'] = User.objects.filter(
            is_superuser=False,
            enrollments__isnull=True
        ).distinct().count()

        return context
