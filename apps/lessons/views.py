from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views import View
from instructors.mixins import InstructorRequiredMixin
from enrollments.models import Enrollment, LessonCompletion
from courses.models import Course
from quizzes.models import Quiz, UserQuizAttempt
from .models import Lesson, Section
from .forms import LessonForm, SectionForm


class LessonPlayerView(LoginRequiredMixin, DetailView):
    model = Lesson
    template_name = 'lessons/player.html'
    context_object_name = 'lesson'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.object
        section = lesson.section
        course = section.course
        
        # Check enrollment
        enrollment = Enrollment.objects.filter(
            user=self.request.user,
            course=course
        ).first()
        
        if not enrollment:
            # Redirect to course detail if not enrolled
            return redirect('course_detail', slug=course.slug)
        
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
        
        # Get user's note for this lesson (if any)
        # This would require a Note model - for now use a placeholder
        context['user_note'] = ""
        
        # Get lesson comments (if comment system exists)
        context['lesson_comments'] = []  # Would need a Comment model
        
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
        
        # Check if course is completed
        total_lessons = sum(section.lessons.count() for section in course.sections.all())
        completed_lessons = LessonCompletion.objects.filter(enrollment=enrollment).count()
        
        if completed_lessons >= total_lessons and total_lessons > 0:
            enrollment.completed = True
            enrollment.save()
            
            # Generate certificate
            from certificates.models import Certificate
            import uuid
            if not hasattr(enrollment, 'certificate'):
                Certificate.objects.create(
                    enrollment=enrollment,
                    certificate_code=str(uuid.uuid4()).replace('-', '').upper()[:16]
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