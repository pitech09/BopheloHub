from django.contrib import admin
from .models import Section, Lesson, LessonNote, LessonComment, LessonResource

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    ordering = ['course', 'order']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'section', 'order']
    ordering = ['section__course', 'section__order', 'order']

@admin.register(LessonNote)
class LessonNoteAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'updated_at']
    search_fields = ['user__username', 'lesson__title']

@admin.register(LessonComment)
class LessonCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'parent', 'created_at']
    list_filter = ['lesson__section__course']
    search_fields = ['user__username', 'text']

@admin.register(LessonResource)
class LessonResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'uploaded_by', 'uploaded_at', 'order']
    list_filter = ['lesson__section__course']
    search_fields = ['title', 'description']
    ordering = ['lesson__section__course', 'lesson__section__order', 'lesson__order', 'order']
