from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.contrib import messages

from .models import Assessment, AssessmentQuestion, AssessmentSubmission, SubmissionAnswer
from .forms import AssessmentForm, AssessmentQuestionForm, AssessmentSubmissionForm
from courses.models import Course
from enrollments.models import Enrollment
from notifications.models import Notification


class InstructorAssessmentMixin(UserPassesTestMixin):
    """Ensures the instructor owns the course."""
    def test_func(self):
        course = self.get_course()
        return course.instructor == self.request.user

    def get_course(self):
        if hasattr(self, 'course'):
            return self.course
        if 'course_id' in self.kwargs:
            return get_object_or_404(Course, pk=self.kwargs['course_id'])
        assessment = get_object_or_404(Assessment, pk=self.kwargs['pk'])
        return assessment.course


class AssessmentListView(LoginRequiredMixin, InstructorAssessmentMixin, ListView):
    model = Assessment
    template_name = 'assessments/list.html'
    context_object_name = 'assessments'

    def get_queryset(self):
        self.course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return Assessment.objects.filter(course=self.course)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context


class AssessmentCreateView(LoginRequiredMixin, InstructorAssessmentMixin, CreateView):
    model = Assessment
    form_class = AssessmentForm
    template_name = 'assessments/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        form.instance.course_id = self.kwargs['course_id']
        messages.success(self.request, 'Assessment created successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('assessment_detail', kwargs={'pk': self.object.pk})


class AssessmentDetailView(LoginRequiredMixin, DetailView):
    model = Assessment
    template_name = 'assessments/detail.html'
    context_object_name = 'assessment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assessment = self.object

        if self.request.user.is_instructor and assessment.course.instructor == self.request.user:
            context['is_instructor'] = True
            context['submissions'] = AssessmentSubmission.objects.filter(assessment=assessment)
            context['enrolled_students'] = Enrollment.objects.filter(
                course=assessment.course, status='active'
            )
        else:
            context['is_instructor'] = False
            enrollment = Enrollment.objects.filter(
                user=self.request.user, course=assessment.course, status='active'
            ).first()
            if enrollment:
                context['enrollment'] = enrollment
                context['submission'] = AssessmentSubmission.objects.filter(
                    assessment=assessment, enrollment=enrollment
                ).first()

        return context


class AssessmentUpdateView(LoginRequiredMixin, InstructorAssessmentMixin, UpdateView):
    model = Assessment
    form_class = AssessmentForm
    template_name = 'assessments/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        context['is_edit'] = True
        return context

    def get_success_url(self):
        return reverse('assessment_detail', kwargs={'pk': self.object.pk})


class AssessmentQuestionCreateView(LoginRequiredMixin, InstructorAssessmentMixin, CreateView):
    model = AssessmentQuestion
    form_class = AssessmentQuestionForm
    template_name = 'assessments/question_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assessment'] = get_object_or_404(Assessment, pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        form.instance.assessment_id = self.kwargs['pk']
        messages.success(self.request, 'Question added successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('assessment_detail', kwargs={'pk': self.object.assessment.pk})


class AssessmentQuestionUpdateView(LoginRequiredMixin, InstructorAssessmentMixin, UpdateView):
    model = AssessmentQuestion
    form_class = AssessmentQuestionForm
    template_name = 'assessments/question_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assessment'] = self.object.assessment
        return context

    def get_success_url(self):
        return reverse('assessment_detail', kwargs={'pk': self.object.assessment.pk})


class AssessmentQuestionDeleteView(LoginRequiredMixin, InstructorAssessmentMixin, DeleteView):
    model = AssessmentQuestion

    def get_success_url(self):
        return reverse('assessment_detail', kwargs={'pk': self.object.assessment.pk})


class AssessmentTakeView(LoginRequiredMixin, TemplateView):
    template_name = 'assessments/take.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assessment = get_object_or_404(Assessment, pk=self.kwargs['pk'])
        enrollment = get_object_or_404(
            Enrollment, user=self.request.user, course=assessment.course, status='active'
        )

        # Check if already submitted
        existing = AssessmentSubmission.objects.filter(
            assessment=assessment, enrollment=enrollment
        ).first()
        if existing:
            context['submission'] = existing
            return context

        context['assessment'] = assessment
        context['questions'] = assessment.questions.all()
        context['enrollment'] = enrollment
        context['form'] = AssessmentSubmissionForm(questions=context['questions'])
        return context

    def post(self, request, *args, **kwargs):
        assessment = get_object_or_404(Assessment, pk=self.kwargs['pk'])
        enrollment = get_object_or_404(
            Enrollment, user=request.user, course=assessment.course, status='active'
        )

        # Check if already submitted
        if AssessmentSubmission.objects.filter(assessment=assessment, enrollment=enrollment).exists():
            messages.error(request, 'You have already submitted this assessment.')
            return redirect('assessment_detail', pk=assessment.pk)

        questions = list(assessment.questions.all())
        form = AssessmentSubmissionForm(request.POST, questions=questions)

        if not form.is_valid():
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)

        with transaction.atomic():
            submission = AssessmentSubmission.objects.create(
                assessment=assessment,
                enrollment=enrollment,
            )

            total_earned = 0
            for q in questions:
                answer_key = f'question_{q.id}'
                answer_text = form.cleaned_data.get(answer_key, '')

                is_correct = None
                points_earned = 0

                if q.question_type == 'multiple_choice':
                    is_correct = (answer_text == q.correct_answer)
                    points_earned = q.points if is_correct else 0
                else:
                    # Essay questions need manual grading
                    is_correct = None
                    points_earned = 0

                total_earned += points_earned

                SubmissionAnswer.objects.create(
                    submission=submission,
                    question=q,
                    answer_text=answer_text if q.question_type == 'essay' else '',
                    selected_option=answer_text if q.question_type == 'multiple_choice' else '',
                    is_correct=is_correct,
                    points_earned=points_earned,
                )

            # Auto-grade if all questions are multiple choice
            if all(q.question_type == 'multiple_choice' for q in questions):
                submission.score = total_earned
                submission.graded = True
                submission.graded_at = assessment.created_at
                submission.save()

        # Notify instructor
        student_name = request.user.get_full_name() or request.user.username
        Notification.objects.create(
            user=assessment.course.instructor,
            message=f'{student_name} submitted "{assessment.title}"',
        )

        messages.success(request, 'Assessment submitted successfully!')
        return redirect('assessment_detail', pk=assessment.pk)


class AssessmentGradeView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = AssessmentSubmission
    template_name = 'assessments/grade.html'
    fields = ['score', 'feedback', 'graded']

    def test_func(self):
        submission = self.get_object()
        return submission.assessment.course.instructor == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submission'] = self.object
        context['answers'] = self.object.answers.all()
        return context

    def form_valid(self, form):
        form.instance.graded = True
        form.instance.graded_by = self.request.user
        from django.utils import timezone
        form.instance.graded_at = timezone.now()

        # Notify student
        Notification.objects.create(
            user=form.instance.enrollment.user,
            message=f'Your assessment "{form.instance.assessment.title}" has been graded. Score: {form.instance.score}/{form.instance.assessment.total_points}',
        )

        messages.success(self.request, 'Assessment graded successfully.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('assessment_detail', kwargs={'pk': self.object.assessment.pk})