from django import forms
from .models import Assessment, AssessmentQuestion, AssessmentSubmission, SubmissionAnswer


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ['title', 'description', 'due_date', 'total_points']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class AssessmentQuestionForm(forms.ModelForm):
    class Meta:
        model = AssessmentQuestion
        fields = ['question_text', 'question_type', 'points', 'order',
                  'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 2}),
            'option_a': forms.TextInput(attrs={'placeholder': 'Option A'}),
            'option_b': forms.TextInput(attrs={'placeholder': 'Option B'}),
            'option_c': forms.TextInput(attrs={'placeholder': 'Option C'}),
            'option_d': forms.TextInput(attrs={'placeholder': 'Option D'}),
        }


class AssessmentSubmissionForm(forms.Form):
    """Dynamic form for answering assessment questions."""
    pass

    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', [])
        super().__init__(*args, **kwargs)
        for q in questions:
            if q.question_type == 'multiple_choice':
                choices = [
                    ('A', f"A. {q.option_a}"),
                    ('B', f"B. {q.option_b}"),
                    ('C', f"C. {q.option_c}"),
                    ('D', f"D. {q.option_d}"),
                ]
                self.fields[f'question_{q.id}'] = forms.ChoiceField(
                    choices=choices,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                    label=q.question_text,
                )
            else:
                self.fields[f'question_{q.id}'] = forms.CharField(
                    widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
                    label=q.question_text,
                    required=True,
                )