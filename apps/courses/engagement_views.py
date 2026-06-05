from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from instructors.mixins import InstructorRequiredMixin
from discussions.models import Discussion, DiscussionReply
from .models import Course
from lessons.models import Lesson, LessonComment


class InstructorEngagementView(InstructorRequiredMixin, ListView):
    """A combined inbox for the instructor to view and reply to all comments & discussions."""
    template_name = 'courses/instructor_engagement.html'
    context_object_name = 'items'
    paginate_by = 20

    def get_queryset(self):
        self.instructor = self.request.user
        self.courses = Course.objects.filter(instructor=self.instructor)
        filter_type = self.request.GET.get('filter', 'all')

        items = []

        # Lesson comments
        if filter_type in ('all', 'comments', 'unanswered_comments'):
            comments_qs = LessonComment.objects.filter(
                lesson__section__course__in=self.courses,
                parent__isnull=True,
            ).select_related('user', 'lesson__section__course').prefetch_related('replies')

            if filter_type == 'unanswered_comments':
                comments_qs = comments_qs.annotate(
                    reply_count=Count('replies')
                ).filter(reply_count=0)

            for c in comments_qs.order_by('-created_at'):
                items.append({
                    'type': 'comment',
                    'id': c.pk,
                    'title': c.text,
                    'body': c.text,
                    'author': c.user,
                    'course': c.lesson.section.course,
                    'lesson': c.lesson,
                    'created_at': c.created_at,
                    'reply_count': c.replies.count(),
                    'needs_response': c.replies.count() == 0,
                    'url': f"/lesson/{c.lesson.pk}/#comment-{c.pk}",
                })

        # Forum discussions
        if filter_type in ('all', 'discussions', 'unanswered_discussions'):
            discussions_qs = Discussion.objects.filter(
                course__in=self.courses,
            ).select_related('user', 'course').prefetch_related('replies')

            if filter_type == 'unanswered_discussions':
                discussions_qs = discussions_qs.annotate(
                    reply_count=Count('replies')
                ).filter(reply_count=0)

            for d in discussions_qs.order_by('-created_at'):
                items.append({
                    'type': 'discussion',
                    'id': d.pk,
                    'title': d.title,
                    'body': d.body,
                    'author': d.user,
                    'course': d.course,
                    'lesson': None,
                    'created_at': d.created_at,
                    'reply_count': d.replies.count(),
                    'needs_response': d.replies.count() == 0,
                    'url': f"/discussions/{d.pk}/",
                    'is_pinned': d.is_pinned,
                })

        # Sort by created_at desc
        items.sort(key=lambda x: x['created_at'], reverse=True)
        return items

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.request.GET.get('filter', 'all')
        context['total_items'] = len(self.get_queryset())

        # Count badges for filter tabs
        self.courses = Course.objects.filter(instructor=self.request.user)
        context['all_count'] = (
            LessonComment.objects.filter(lesson__section__course__in=self.courses, parent__isnull=True).count()
            + Discussion.objects.filter(course__in=self.courses).count()
        )
        context['comments_count'] = LessonComment.objects.filter(
            lesson__section__course__in=self.courses, parent__isnull=True
        ).count()
        context['discussions_count'] = Discussion.objects.filter(course__in=self.courses).count()
        context['unanswered_comments_count'] = LessonComment.objects.filter(
            lesson__section__course__in=self.courses, parent__isnull=True
        ).annotate(rc=Count('replies')).filter(rc=0).count()
        context['unanswered_discussions_count'] = Discussion.objects.filter(
            course__in=self.courses
        ).annotate(rc=Count('replies')).filter(rc=0).count()
        return context
