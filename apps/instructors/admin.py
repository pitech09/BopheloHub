from django.contrib import admin
from .models import InstructorProfile

@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'headline', 'phone']
    list_filter = ['status']
    actions = ['approve_instructors', 'reject_instructors']

    def approve_instructors(self, request, queryset):
        queryset.update(status='verified')
    approve_instructors.short_description = "Approve selected instructors"

    def reject_instructors(self, request, queryset):
        queryset.update(status='rejected')
    reject_instructors.short_description = "Reject selected instructors"