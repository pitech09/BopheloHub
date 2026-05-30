from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class StudentRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_instructor = False
        user.username = user.email.split('@')[0]   # temporary; save() will sanitize
        if commit:
            user.save()
        return user

class InstructorRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_instructor = True          # flag as instructor (but still unverified)
        user.username = user.email.split('@')[0]
        if commit:
            user.save()
        return user