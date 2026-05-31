from django import forms
from django.forms import modelformset_factory
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Section, Lesson
from quizzes.models import Quiz, Question, Choice

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['title', 'order']

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'order', 'content', 'video_url']
        widgets = {
            'content': CKEditor5Widget(config_name='extends')
        }


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'pass_percentage']
        widgets = {
            'pass_percentage': forms.NumberInput(attrs={'min': 70, 'max': 100}),
        }

    def clean_pass_percentage(self):
        value = self.cleaned_data['pass_percentage']
        if value < 70:
            raise forms.ValidationError('The pass mark must be at least 70%.')
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter the question students must answer...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget.attrs.setdefault('class', 'form-control')


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'placeholder': 'Answer option'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget.attrs.setdefault('class', 'form-control')
        self.fields['is_correct'].widget.attrs.setdefault('class', 'form-check-input')


ChoiceFormSet = modelformset_factory(
    Choice,
    form=ChoiceForm,
    extra=4,
    min_num=4,
    max_num=4,
    validate_min=True,
    validate_max=True,
    can_delete=False,
)
