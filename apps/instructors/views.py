from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from .models import InstructorProfile
from .forms import InstructorApplicationForm

class InstructorApplicationView(LoginRequiredMixin, CreateView):
    model = InstructorProfile
    form_class = InstructorApplicationForm
    template_name = 'instructors/apply.html'
    success_url = '/profile/'    # or reverse_lazy('profile')

    def form_valid(self, form):
        profile = form.save(commit=False)
        profile.user = self.request.user
        profile.status = 'pending'   # reset to pending on re-submission
        profile.save()
        return redirect(self.success_url)