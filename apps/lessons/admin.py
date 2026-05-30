from django.contrib import admin
from .models import Section, Lesson

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    ordering = ['course', 'order']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'order']
    ordering = ['section__course', 'section__order', 'order']