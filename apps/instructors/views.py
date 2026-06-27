from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from django.db import IntegrityError
from django.contrib import messages
from .models import InstructorProfile
from .forms import InstructorApplicationForm

class InstructorApplicationView(LoginRequiredMixin, CreateView):
    model = InstructorProfile
    form_class = InstructorApplicationForm
    template_name = 'instructors/apply.html'
    success_url = '/profile/'    # or reverse_lazy('profile')

    def form_valid(self, form):
        existing = InstructorProfile.objects.filter(user=self.request.user).first()
        id_document = form.cleaned_data.get('id_document') or (existing.id_document if existing else None)
        try:
            profile, _ = InstructorProfile.objects.update_or_create(
                user=self.request.user,
                defaults={
                    'headline': form.cleaned_data.get('headline', ''),
                    'website': form.cleaned_data.get('website', ''),
                    'phone': form.cleaned_data.get('phone', ''),
                    'qualifications': form.cleaned_data.get('qualifications', ''),
                    'id_document': id_document,
                    'status': 'pending',
                }
            )
        except IntegrityError:
            form.add_error(
                None,
                'We could not save your application. Please try using different details.'
            )
            return self.form_invalid(form)

        messages.success(self.request, 'Your instructor application has been submitted for review.')
        return redirect(self.success_url)
