from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.urls import reverse
from django.db.models import Count, Q

from courses.models import Course
from enrollments.models import Enrollment
from .models import Discussion, DiscussionReply
from .forms import DiscussionForm, DiscussionReplyForm


class CourseDiscussionListView(LoginRequiredMixin, ListView):
    """List all discussions for a specific course."""
    model = Discussion
    template_name = 'discussions/course_discussions.html'
    context_object_name = 'discussions'
    paginate_by = 20

    def get_queryset(self):
        self.course = get_object_or_404(Course, slug=self.kwargs['slug'])
        return Discussion.objects.filter(course=self.course).select_related(
            'user'
        ).annotate(
            reply_count=Count('replies')
        ).order_by('-is_pinned', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        context['is_enrolled'] = Enrollment.objects.filter(
            user=self.request.user,
            course=self.course,
            status='active'
        ).exists()
        context['form'] = DiscussionForm()
        return context


class DiscussionDetailView(LoginRequiredMixin, DetailView):
    """View a single discussion thread with replies."""
    model = Discussion
    template_name = 'discussions/discussion_detail.html'
    context_object_name = 'discussion'

    def get_queryset(self):
        return Discussion.objects.select_related('user', 'course').annotate(
            reply_count=Count('replies')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        discussion = self.object
        course = discussion.course
        context['course'] = course
        context['is_enrolled'] = Enrollment.objects.filter(
            user=self.request.user,
            course=course,
            status='active'
        ).exists()
        context['is_instructor'] = course.instructor == self.request.user
        context['replies'] = discussion.replies.select_related('user').order_by('created_at')
        context['reply_form'] = DiscussionReplyForm()
        return context


@login_required
def create_discussion(request, slug):
    """Create a new discussion thread in a course."""
    course = get_object_or_404(Course, slug=slug)

    # Verify user is enrolled (or is the instructor)
    is_enrolled = Enrollment.objects.filter(
        user=request.user,
        course=course,
        status='active'
    ).exists()
    is_instructor = course.instructor == request.user

    if not is_enrolled and not is_instructor:
        messages.error(request, 'You must be enrolled in this course to start a discussion.')
        return redirect('course_detail', slug=course.slug)

    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.course = course
            discussion.user = request.user
            discussion.save()

            # Notify the instructor
            from notifications.models import Notification
            Notification.objects.create(
                user=course.instructor,
                message=f'New discussion: "{discussion.title}" in {course.title}'
            )

            messages.success(request, 'Your discussion has been posted!')
            return redirect('discussions:discussion_detail', pk=discussion.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = DiscussionForm()

    return render(request, 'discussions/discussion_form.html', {
        'form': form,
        'course': course,
        'is_enrolled': is_enrolled,
    })


@login_required
def reply_to_discussion(request, pk):
    """Post a reply to a discussion thread."""
    discussion = get_object_or_404(Discussion, pk=pk)
    course = discussion.course

    # Verify user is enrolled or is the instructor
    is_enrolled = Enrollment.objects.filter(
        user=request.user,
        course=course,
        status='active'
    ).exists()
    is_instructor = course.instructor == request.user

    if not is_enrolled and not is_instructor:
        messages.error(request, 'You must be enrolled in this course to reply.')
        return redirect('course_detail', slug=course.slug)

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')

    if discussion.is_closed:
        messages.warning(request, 'This discussion is closed for new replies.')
        if next_url:
            from django.utils.http import url_has_allowed_host_and_scheme
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
        return redirect('discussions:discussion_detail', pk=discussion.pk)

    if request.method == 'POST':
        form = DiscussionReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.discussion = discussion
            reply.user = request.user
            reply.save()

            # Notify other participants (except the replier)
            from notifications.models import Notification
            participants = set()
            participants.add(discussion.user)
            for r in discussion.replies.all():
                participants.add(r.user)
            participants.discard(request.user)

            for participant in participants:
                name = request.user.get_full_name() or request.user.username
                Notification.objects.create(
                    user=participant,
                    message=f'New reply from {name} in "{discussion.title}"'
                )

            messages.success(request, 'Your reply has been posted!')

            # Redirect back to the page the user came from (engagement, dashboard, etc.)
            if next_url:
                from django.utils.http import url_has_allowed_host_and_scheme
                if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                    return redirect(next_url)
            return redirect('discussions:discussion_detail', pk=discussion.pk)
    else:
        form = DiscussionReplyForm()

    return render(request, 'discussions/discussion_detail.html', {
        'discussion': discussion,
        'course': course,
        'replies': discussion.replies.select_related('user').order_by('created_at'),
        'reply_form': form,
        'is_enrolled': is_enrolled,
        'is_instructor': is_instructor,
    })
