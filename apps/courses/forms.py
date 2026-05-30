from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Course

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'slug', 'category', 'description', 'thumbnail', 'price', 'is_published']
        widgets = {
            'description': CKEditor5Widget(config_name='extends')
        }