from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Avg, Prefetch
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
        ).filter(course_count__gt=0)[:8]
        return context


class InstructorDashboardView(InstructorRequiredMixin, ListView):
    model = Course
    template_name = 'courses/instructor_dashboard.html'
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user).annotate(
            enrolled_count=Count('enrollments'),
            average_rating=Avg('reviews__rating')
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses = self.get_queryset()
        context['total_enrollments'] = Enrollment.objects.filter(course__in=courses).count()
        context['total_revenue'] = sum(c.price for c in courses if c.price > 0)
        context['average_rating'] = courses.aggregate(Avg('average_rating'))['average_rating__avg'] or 0
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
        ).filter(course_count__gt=0)
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
            context['is_enrolled'] = Enrollment.objects.filter(
                user=self.request.user,
                course=course
            ).exists()
        else:
            context['is_enrolled'] = False
        
        # Get reviews
        context['reviews'] = course.reviews.all()[:10]
        
        # Calculate average rating
        context['average_rating'] = course.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        context['review_count'] = course.reviews.count()
        
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


class EnrollCourseView(LoginRequiredMixin, DetailView):
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
        
        # If course is free, enroll directly
        if course.price == 0:
            enrollment = Enrollment.objects.create(
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
            # For paid courses, redirect to payment page
            return redirect('enroll_course', slug=course.slug)
