from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Section, Lesson

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