from django import forms
from .models import Discussion, DiscussionReply


class DiscussionForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a descriptive title for your question/discussion...',
                'maxlength': 255,
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe your question or discussion topic in detail...',
            }),
        }
        labels = {
            'title': 'Discussion Title',
            'body': 'Details',
        }


class DiscussionReplyForm(forms.ModelForm):
    class Meta:
        model = DiscussionReply
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your reply...',
            }),
        }
        labels = {
            'body': 'Your Reply',
        }