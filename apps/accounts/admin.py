from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['email', 'first_name', 'last_name', 'is_instructor', 'is_staff']
    ordering = ['email']
    fieldsets = UserAdmin.fieldsets + (
        ('Extra', {'fields': ('is_instructor', 'bio', 'profile_picture')}),
    )

admin.site.register(User, CustomUserAdmin)