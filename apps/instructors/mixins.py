from django.contrib.auth.mixins import AccessMixin

class InstructorRequiredMixin(AccessMixin):
    """Verify that the current user is an instructor and is verified."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_instructor:
            return self.handle_no_permission()
        try:
            profile = request.user.instructor_profile
            if profile.status != 'verified':
                return self.handle_no_permission()
        except:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)