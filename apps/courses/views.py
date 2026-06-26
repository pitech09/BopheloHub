from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Avg, Prefetch, Case, When, IntegerField
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from enrollments.models import Enrollment
from instructors.mixins import InstructorRequiredMixin
from reviews.models import Review
from notifications.models import Notification
from .models import Course, Category
from .forms import CourseForm


class HomeView(TemplateView):
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_courses'] = Course.objects.filter(is_published=True).annotate(
            enrolled_count=Count('enrollments'),
            average_rating=Avg('reviews__rating')
        ).order_by('-enrolled_count', '-average_rating')[:6]
        context['categories'] = Category.objects.annotate(
            course_count=Count('courses', filter=Q(courses__is_published=True))
        ).order_by('name')
        return context


class InstructorDashboardView(InstructorRequiredMixin, ListView):
    model = Course
    template_name = 'courses/instructor_dashboard.html'
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user).annotate(
            enrolled_count=Count('enrollments'),
            average_rating=Avg('reviews__rating'),
            total_reviews=Count('reviews'),
            total_sections=Count('sections', distinct=True),
            discussion_count=Count('discussions', distinct=True),
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses = self.get_queryset()
        user = self.request.user

        # ── Overall Stats ──
        total_courses = courses.count()
        published_courses = courses.filter(is_published=True).count()
        active_enrollments = Enrollment.objects.filter(course__in=courses, status='active').count()
        pending_enrollments = Enrollment.objects.filter(course__in=courses, status='pending').count()
        total_enrollments = active_enrollments + pending_enrollments
        avg_rating = courses.aggregate(Avg('average_rating'))['average_rating__avg'] or 0
        total_students = Enrollment.objects.filter(
            course__in=courses, status='active'
        ).values('user').distinct().count()

        # ── Revenue Calculation (85% instructor commission on verified payments) ──
        from payments.models import Payment
        from django.db.models import Sum
        INSTRUCTOR_COMMISSION = 0.85  # 85% payout rate

        verified_payments = Payment.objects.filter(
            course__in=courses,
            status='verified'
        ).aggregate(total=Sum('amount'))
        gross_revenue = verified_payments['total'] or 0
        net_revenue = float(gross_revenue) * INSTRUCTOR_COMMISSION  # Instructor's 85% cut

        context.update({
            'total_courses': total_courses,
            'published_courses': published_courses,
            'total_enrollments': total_enrollments,
            'total_students': total_students,
            'total_revenue': net_revenue,
            'gross_revenue': float(gross_revenue),
            'commission_rate': int(INSTRUCTOR_COMMISSION * 100),
            'average_rating': round(avg_rating, 1),
        })

        # ── Top Performing Course ──
        top_course = courses.order_by('-enrolled_count').first()
        context['top_course'] = top_course

        # ── Recent Enrollments (last 5) ──
        recent_enrollments = Enrollment.objects.filter(
            course__in=courses
        ).select_related('user', 'course').order_by('-enrolled_at')[:5]
        context['recent_enrollments'] = recent_enrollments

        # ── Enrollments per course (for chart/data) ──
        enrollment_data = []
        for c in courses:
            if c.enrolled_count > 0:
                enrollment_data.append({
                    'title': c.title,
                    'count': c.enrolled_count,
                })
        context['enrollment_data'] = enrollment_data

        # ── Students per course ──
        course_students = {}
        for c in courses:
            students = Enrollment.objects.filter(
                course=c, status='active'
            ).select_related('user').order_by('-enrolled_at')
            course_students[c.id] = {
                'course': c,
                'students_count': students.count(),
                'students': students[:10],  # Show top 10
                'has_more': students.count() > 10,
            }
        context['course_students'] = course_students

        # ── Recent Discussions per course ──
        from discussions.models import Discussion
        recent_discussions = Discussion.objects.filter(
            course__in=courses
        ).select_related('user', 'course').order_by('-created_at')[:10]
        context['recent_discussions'] = recent_discussions

        # Unanswered discussions (no replies)
        unanswered = Discussion.objects.filter(
            course__in=courses,
            is_closed=False
        ).annotate(reply_count=Count('replies')).filter(reply_count=0).order_by('-created_at')
        context['unanswered_discussions'] = unanswered[:5]

        # ── Recent Lesson Comments (from lesson player) ──
        from lessons.models import LessonComment
        recent_lesson_comments = LessonComment.objects.filter(
            parent__isnull=True,  # Only top-level (not replies)
            lesson__section__course__in=courses
        ).select_related('user', 'lesson__section__course').order_by('-created_at')[:10]
        context['recent_lesson_comments'] = recent_lesson_comments

        # Unanswered lesson comments (no replies)
        unanswered_lesson_comments = LessonComment.objects.filter(
            parent__isnull=True,
            replies__isnull=True,
            lesson__section__course__in=courses
        ).select_related('user', 'lesson__section__course').order_by('-created_at')[:5]
        context['unanswered_lesson_comments'] = unanswered_lesson_comments

        # ── Reviews stats per course ──
        from reviews.models import Review
        recent_reviews = Review.objects.filter(
            course__in=courses
        ).select_related('user', 'course').order_by('-created_at')[:5]
        context['recent_reviews'] = recent_reviews

        return context


class CourseCreateView(InstructorRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('instructor_dashboard')

    def form_valid(self, form):
        form.instance.instructor = self.request.user
        return super().form_valid(form)


class CourseUpdateView(InstructorRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('instructor_dashboard')

    def get_queryset(self):
        # ensure instructor can only edit their own courses
        return Course.objects.filter(instructor=self.request.user)
    

class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12

    def get_queryset(self):
        queryset = Course.objects.filter(is_published=True).select_related('instructor', 'category')
        
        # Search functionality
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(instructor__first_name__icontains=query) |
                Q(instructor__last_name__icontains=query)
            )
        
        # Category filter
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Annotate with ratings and enrollment count
        queryset = queryset.annotate(
            enrolled_count=Count('enrollments'),
            average_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        
        # Sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['title', '-title', 'price', '-price', 'average_rating', '-average_rating']:
            queryset = queryset.order_by(sort_by)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(
            course_count=Count('courses', filter=Q(courses__is_published=True))
        ).order_by('name')
        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_queryset(self):
        return Course.objects.filter(is_published=True).prefetch_related(
            'sections__lessons',
            Prefetch('reviews', queryset=Review.objects.select_related('user').order_by('-created_at'))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        
        # Get enrollment status
        if self.request.user.is_authenticated:
            enrollment = Enrollment.objects.filter(
                user=self.request.user,
                course=course
            ).first()
            context['is_enrolled'] = enrollment and enrollment.status == 'active'
            context['has_pending_enrollment'] = enrollment and enrollment.status == 'pending'
        else:
            context['is_enrolled'] = False
            context['has_pending_enrollment'] = False
        
        
        # Get reviews
        reviews_qs = course.reviews.select_related('user').order_by('-created_at')
        context['reviews'] = reviews_qs[:10]
        context['review_count'] = reviews_qs.count()
        
        # Calculate average rating
        avg_rating = reviews_qs.aggregate(Avg('rating'))['rating__avg'] or 0
        context['average_rating'] = avg_rating
        
        # Rating distribution
        context['rating_counts'] = {
            i: reviews_qs.filter(rating=i).count() for i in range(5, 0, -1)
        }
        
        # Recommendation percentage (4+ star ratings)
        if context['review_count'] > 0:
            recommended = reviews_qs.filter(rating__gte=4).count()
            context['recommendation_percentage'] = round((recommended / context['review_count']) * 100)
        else:
            context['recommendation_percentage'] = 0
        
        # Recent review count (last 30 days)
        from django.utils import timezone
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        context['recent_review_count'] = reviews_qs.filter(created_at__gte=thirty_days_ago).count()
        
        # Current user's review (for edit/delete)
        if self.request.user.is_authenticated:
            context['user_review'] = reviews_qs.filter(user=self.request.user).first()
        else:
            context['user_review'] = None
        
        # Get first lesson for enrollment
        first_lesson = course.sections.first()
        if first_lesson:
            first_lesson = first_lesson.lessons.first()
        context['first_lesson_id'] = first_lesson.pk if first_lesson else None
        
        # Calculate total lessons
        context['total_lessons'] = sum(section.lessons.count() for section in course.sections.all())
        
        # Enrolled count
        context['enrolled_count'] = course.enrollments.count()
        
        return context


class EnrollFreeCourseView(LoginRequiredMixin, DetailView):
    """Handles direct enrollment for free courses."""
    model = Course
    
    def post(self, request, *args, **kwargs):
        course = get_object_or_404(Course, slug=self.kwargs['slug'], is_published=True)
        
        # Check if already has enrollment
        existing = Enrollment.objects.filter(user=request.user, course=course).first()
        if existing:
            if existing.status == 'active':
                messages.info(request, 'You are already enrolled in this course.')
            elif existing.status == 'pending':
                messages.info(request, 'Your enrollment is pending payment verification.')
            return redirect('course_detail', slug=course.slug)
        
        # Only free courses can be enrolled via POST
        if course.price == 0:
            Enrollment.objects.create(
                user=request.user,
                course=course,
                status='active'
            )
            Notification.objects.create(
                user=request.user,
                message=f'You have successfully enrolled in {course.title}'
            )
            messages.success(request, f'You are now enrolled in {course.title}!')
            return redirect('course_detail', slug=course.slug)
        else:
            # Paid courses go through payment form
            return redirect('enroll_course', slug=course.slug)
