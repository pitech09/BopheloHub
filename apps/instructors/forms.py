from django import forms
from .models import InstructorProfile

class InstructorApplicationForm(forms.ModelForm):
    class Meta:
        model = InstructorProfile
        fields = ['headline', 'website', 'phone', 'qualifications', 'id_document']