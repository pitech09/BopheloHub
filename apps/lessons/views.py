from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views import View
from instructors.mixins import InstructorRequiredMixin
from enrollments.models import Enrollment, LessonCompletion
from courses.models import Course
from quizzes.models import Quiz, UserQuizAttempt, Question, Choice
from .models import Lesson, Section, LessonNote, LessonComment, LessonResource
from .forms import LessonForm, SectionForm, QuizForm, QuestionForm, ChoiceFormSet, LessonResourceForm
from django.views.decorators.http import require_POST


@require_POST
@login_required
def save_note(request, pk):
    """Save or update a student's note for a lesson."""
    lesson = get_object_or_404(Lesson, pk=pk)
    content = request.POST.get('content', '').strip()
    note, created = LessonNote.objects.update_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'content': content}
    )
    messages.success(request, 'Note saved successfully.')
    return redirect('lesson_play', pk=lesson.pk)


@require_POST
@login_required
def post_comment(request, pk):
    """Post a comment on a lesson (or reply to a comment)."""
    lesson = get_object_or_404(Lesson, pk=pk)
    text = request.POST.get('text', '').strip()
    parent_id = request.POST.get('parent_id')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')

    if text:
        parent = None
        if parent_id:
            parent = get_object_or_404(LessonComment, pk=parent_id, lesson=lesson)

        comment = LessonComment.objects.create(
            user=request.user,
            lesson=lesson,
            parent=parent,
            text=text
        )

        # Notify the instructor (if it's a top-level comment)
        if not parent:
            from notifications.models import Notification
            name = request.user.get_full_name() or request.user.username
            Notification.objects.create(
                user=lesson.section.course.instructor,
                message=f'New comment from {name} on lesson "{lesson.title}"'
            )
        # Notify the parent comment author (if it's a reply and not replying to self)
        elif parent.user != request.user:
            from notifications.models import Notification
            name = request.user.get_full_name() or request.user.username
            Notification.objects.create(
                user=parent.user,
                message=f'{name} replied to your comment on "{lesson.title}"'
            )

        messages.success(request, 'Comment posted successfully.')
    else:
        messages.error(request, 'Comment cannot be empty.')

    # Redirect back to the page the user came from (engagement, dashboard, etc.)
    if next_url and next_url != request.build_absolute_uri():
        from django.utils.http import url_has_allowed_host_and_scheme
        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return redirect(next_url)
    return redirect('lesson_play', pk=lesson.pk)


# Lesson Resource Management Views (Instructor only)
class LessonResourceCreateView(InstructorRequiredMixin, CreateView):
    model = LessonResource
    form_class = LessonResourceForm
    template_name = 'lessons/resource_form.html'
    
    def get_success_url(self):
        return reverse_lazy('lesson_play', kwargs={'pk': self.object.lesson.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {'lesson': self.kwargs['lesson_pk']}
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lesson'] = get_object_or_404(Lesson, pk=self.kwargs['lesson_pk'], section__course__instructor=self.request.user)
        context['course'] = context['lesson'].section.course
        return context
    
    def form_valid(self, form):
        lesson = get_object_or_404(Lesson, pk=self.kwargs['lesson_pk'], section__course__instructor=self.request.user)
        form.instance.lesson = lesson
        form.instance.uploaded_by = self.request.user
        return super().form_valid(form)


class LessonResourceUpdateView(InstructorRequiredMixin, UpdateView):
    model = LessonResource
    form_class = LessonResourceForm
    template_name = 'lessons/resource_form.html'
    
    def get_queryset(self):
        return LessonResource.objects.filter(lesson__section__course__instructor=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy('lesson_play', kwargs={'pk': self.object.lesson.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lesson'] = self.object.lesson
        context['course'] = self.object.lesson.section.course
        return context


class LessonResourceDeleteView(InstructorRequiredMixin, DeleteView):
    model = LessonResource
    template_name = 'lessons/resource_confirm_delete.html'
    
    def get_queryset(self):
        return LessonResource.objects.filter(lesson__section__course__instructor=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy('lesson_play', kwargs={'pk': self.object.lesson.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lesson'] = self.object.lesson
        context['course'] = self.object.lesson.section.course
        return context


class LessonPlayerView(LoginRequiredMixin, DetailView):
    model = Lesson
    template_name = 'lessons/player.html'
    context_object_name = 'lesson'
    
    def dispatch(self, request, *args, **kwargs):
        lesson = self.get_object()
        section = lesson.section
        course = section.course
        
        # Check enrollment before proceeding
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=course
        ).first()
        
        if not enrollment:
            return redirect('course_detail', slug=course.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.object
        section = lesson.section
        course = section.course
        
        enrollment = Enrollment.objects.filter(
            user=self.request.user,
            course=course
        ).first()
        
        context['course'] = course
        context['section_title'] = section.title
        
        # Get all sections with lessons for sidebar
        context['sections'] = course.sections.prefetch_related('lessons').order_by('order')
        
        # Get completed lessons
        completed_lessons = LessonCompletion.objects.filter(
            enrollment=enrollment
        ).values_list('lesson_id', flat=True)
        context['completed_lessons'] = list(completed_lessons)
        
        # Check if current lesson is completed
        context['is_completed'] = lesson.pk in completed_lessons
        
        # Get previous and next lessons
        lesson_ids = list(course.sections.order_by('order').values_list('lessons', flat=True))
        
        current_index = lesson_ids.index(lesson.pk) if lesson.pk in lesson_ids else -1
        
        if current_index > 0:
            context['previous_lesson'] = Lesson.objects.get(pk=lesson_ids[current_index - 1])
        else:
            context['previous_lesson'] = None
            
        if current_index < len(lesson_ids) - 1:
            context['next_lesson'] = Lesson.objects.get(pk=lesson_ids[current_index + 1])
        else:
            context['next_lesson'] = None
        
        # Calculate course progress
        total_lessons = len(lesson_ids)
        completed_count = len(completed_lessons)
        context['course_progress'] = (completed_count / total_lessons * 100) if total_lessons > 0 else 0
        
        # Get user's note for this lesson
        note = LessonNote.objects.filter(user=self.request.user, lesson=lesson).first()
        context['user_note'] = note.content if note else ""
        
        # Get lesson comments
        context['lesson_comments'] = LessonComment.objects.filter(
            lesson=lesson
        ).select_related('user').order_by('created_at')
        
        # Get top-level comment count for the badge
        context['comment_count'] = LessonComment.objects.filter(
            lesson=lesson,
            parent__isnull=True
        ).count()
        
        # Check if user is instructor for this course
        context['is_instructor'] = course.instructor == self.request.user
        
        return context


class CompleteLessonView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        lesson = get_object_or_404(Lesson, pk=self.kwargs['pk'])
        section = lesson.section
        course = section.course
        
        # Get enrollment
        enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
        
        # Mark lesson as complete
        LessonCompletion.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson
        )
        
        certificate = enrollment.complete_and_issue_certificate_if_eligible()
        if certificate:
            messages.success(
                request,
                'Congratulations! You passed the course requirements and your certificate is ready.'
            )
        
        # Redirect to next lesson or course detail
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        
        # Get next lesson
        lesson_ids = list(course.sections.order_by('order').values_list('lessons', flat=True))
        
        if lesson.pk in lesson_ids:
            current_index = lesson_ids.index(lesson.pk)
            if current_index < len(lesson_ids) - 1:
                return redirect('lesson_play', pk=lesson_ids[current_index + 1])
        
        return redirect('course_detail', slug=course.slug)


class QuizTakeView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = 'quizzes/take.html'
    context_object_name = 'quiz'

    def dispatch(self, request, *args, **kwargs):
        quiz = self.get_object()
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=quiz.lesson.section.course,
            status='active',
        ).first()
        if not enrollment:
            messages.warning(request, 'You need an active enrollment to take this quiz.')
            return redirect('course_detail', slug=quiz.lesson.section.course.slug)
        if not quiz.questions.exists():
            messages.warning(request, 'This quiz is not ready yet. The instructor still needs to add questions.')
            return redirect('lesson_play', pk=quiz.lesson.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.object
        
        # Check if user has already passed this quiz
        attempt = UserQuizAttempt.objects.filter(
            user=self.request.user,
            quiz=quiz,
            passed=True
        ).first()
        context['passed_attempt'] = attempt
        
        # Get user's best score
        best_attempt = UserQuizAttempt.objects.filter(
            user=self.request.user,
            quiz=quiz
        ).order_by('-score').first()
        context['best_score'] = best_attempt.score if best_attempt else None
        
        # Get previous attempts
        context['attempts'] = UserQuizAttempt.objects.filter(
            user=self.request.user,
            quiz=quiz
        ).order_by('-attempted_at')[:5]
        
        return context
    
    def post(self, request, *args, **kwargs):
        quiz = self.get_object()
        
        # Get answers from form
        answers = {}
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = int(key.split('_')[1])
                answers[question_id] = int(value)
        
        # Calculate score
        total_questions = quiz.questions.count()
        if total_questions == 0:
            messages.warning(request, 'This quiz is not ready yet. The instructor still needs to add questions.')
            return redirect('lesson_play', pk=quiz.lesson.pk)

        correct_answers = 0
        
        for question in quiz.questions.all():
            if question.pk in answers:
                selected_choice_id = answers[question.pk]
                correct_choice = question.choices.filter(is_correct=True).first()
                if correct_choice and correct_choice.pk == selected_choice_id:
                    correct_answers += 1
        
        score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        passed = score >= quiz.pass_percentage
        
        # Save attempt
        attempt = UserQuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            passed=passed
        )

        if passed:
            enrollment = Enrollment.objects.filter(
                user=request.user,
                course=quiz.lesson.section.course,
            ).first()
            if enrollment:
                certificate = enrollment.complete_and_issue_certificate_if_eligible()
                if certificate:
                    messages.success(
                        request,
                        'Congratulations! You passed the course requirements and your certificate is ready.'
                    )
        
        if passed:
            return redirect('quiz_result', pk=attempt.pk)
        else:
            return redirect('quiz_take', pk=quiz.pk)


class QuizResultView(LoginRequiredMixin, DetailView):
    model = UserQuizAttempt
    template_name = 'quizzes/result.html'
    context_object_name = 'attempt'
    
    def get_queryset(self):
        return UserQuizAttempt.objects.filter(user=self.request.user)


# Instructor views for lesson management

class LessonCreateView(InstructorRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'lessons/lesson_form.html'
    
    def get_success_url(self):
        return reverse_lazy('curriculum', kwargs={'pk': self.object.section.course.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['section'] = get_object_or_404(Section, pk=self.kwargs.get('section_pk'))
        context['course'] = context['section'].course
        return context
    
    def form_valid(self, form):
        form.instance.section_id = self.kwargs.get('section_pk')
        return super().form_valid(form)


class LessonUpdateView(InstructorRequiredMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'lessons/lesson_form.html'
    
    def get_success_url(self):
        return reverse_lazy('curriculum', kwargs={'pk': self.object.section.course.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.section.course
        return context


class LessonDeleteView(InstructorRequiredMixin, DeleteView):
    model = Lesson
    template_name = 'lessons/lesson_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('curriculum', kwargs={'pk': self.object.section.course.pk})


class SectionCreateView(InstructorRequiredMixin, CreateView):
    model = Section
    form_class = SectionForm
    template_name = 'lessons/section_form.html'
    
    def get_success_url(self):
        return reverse_lazy('curriculum', kwargs={'pk': self.kwargs.get('course_pk')})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs.get('course_pk'))
        return context
    
    def form_valid(self, form):
        form.instance.course_id = self.kwargs.get('course_pk')
        return super().form_valid(form)


class SectionUpdateView(InstructorRequiredMixin, UpdateView):
    model = Section
    form_class = SectionForm
    template_name = 'lessons/section_form.html'
    
    def get_success_url(self):
        return reverse_lazy('curriculum', kwargs={'pk': self.object.course.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context


class SectionDeleteView(InstructorRequiredMixin, DeleteView):
    model = Section
    template_name = 'lessons/section_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('curriculum', kwargs={'pk': self.object.course.pk})


class CurriculumView(InstructorRequiredMixin, DetailView):
    model = Course
    template_name = 'lessons/curriculum.html'
    context_object_name = 'course'
    
    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user).prefetch_related(
            'sections__lessons'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sections'] = self.object.sections.prefetch_related('lessons').order_by('order')
        return context


class ReorderLessonsView(InstructorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        section_id = kwargs.get('section_pk')
        lesson_ids = request.POST.getlist('lesson_ids[]')
        
        for index, lesson_id in enumerate(lesson_ids):
            Lesson.objects.filter(pk=lesson_id, section_id=section_id).update(order=index)
        
        return JsonResponse({'success': True})


class ReorderSectionsView(InstructorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        course_id = kwargs.get('course_pk')
        section_ids = request.POST.getlist('section_ids[]')
        
        for index, section_id in enumerate(section_ids):
            Section.objects.filter(pk=section_id, course_id=course_id).update(order=index)
        
        return JsonResponse({'success': True})


class QuizManageView(InstructorRequiredMixin, View):
    template_name = 'lessons/quiz_manage.html'

    def get_lesson(self):
        return get_object_or_404(
            Lesson,
            pk=self.kwargs['lesson_pk'],
            section__course__instructor=self.request.user,
        )

    def get_quiz(self, lesson):
        quiz, _ = Quiz.objects.get_or_create(
            lesson=lesson,
            defaults={
                'title': f'{lesson.title} Quiz',
                'pass_percentage': 70,
            },
        )
        return quiz

    def get(self, request, *args, **kwargs):
        lesson = self.get_lesson()
        quiz = self.get_quiz(lesson)
        return self.render_form(lesson, quiz)

    def post(self, request, *args, **kwargs):
        lesson = self.get_lesson()
        quiz = self.get_quiz(lesson)
        quiz_form = QuizForm(request.POST, instance=quiz)
        question_form = QuestionForm(request.POST)
        formset = ChoiceFormSet(request.POST)

        if quiz_form.is_valid() and question_form.is_valid() and formset.is_valid():
            quiz = quiz_form.save()
            question = question_form.save(commit=False)
            question.quiz = quiz
            question.order = quiz.questions.count() + 1
            question.save()

            correct_count = 0
            for form in formset:
                if not form.cleaned_data:
                    continue
                choice = form.save(commit=False)
                choice.question = question
                choice.save()
                if choice.is_correct:
                    correct_count += 1

            if correct_count != 1:
                question.delete()
                messages.error(request, 'Each question must have exactly one correct answer.')
                return self.render_form(lesson, quiz, quiz_form, question_form, formset)

            messages.success(request, 'Question added. Students must score at least 70% before a certificate can be issued.')
            return redirect('quiz_manage', lesson_pk=lesson.pk)

        return self.render_form(lesson, quiz, quiz_form, question_form, formset)

    def render_form(self, lesson, quiz, quiz_form=None, question_form=None, formset=None):
        from django.shortcuts import render
        context = {
            'course': lesson.section.course,
            'section': lesson.section,
            'lesson': lesson,
            'quiz': quiz,
            'quiz_form': quiz_form or QuizForm(instance=quiz),
            'question_form': question_form or QuestionForm(),
            'choice_formset': formset or ChoiceFormSet(queryset=Choice.objects.none()),
        }
        return render(self.request, self.template_name, context)


class QuestionDeleteView(InstructorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        question = get_object_or_404(
            Question,
            pk=self.kwargs['pk'],
            quiz__lesson__section__course__instructor=request.user,
        )
        lesson_pk = question.quiz.lesson.pk
        question.delete()
        messages.success(request, 'Question removed.')
        return redirect('quiz_manage', lesson_pk=lesson_pk)
