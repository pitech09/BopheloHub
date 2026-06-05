from django.contrib import admin
from .models import Discussion, DiscussionReply


class DiscussionReplyInline(admin.TabularInline):
    model = DiscussionReply
    extra = 0
    readonly_fields = ['user', 'body', 'created_at']


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'user', 'is_pinned', 'is_closed', 'reply_count', 'created_at']
    list_filter = ['is_pinned', 'is_closed', 'course']
    search_fields = ['title', 'body', 'course__title']
    inlines = [DiscussionReplyInline]


@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin):
    list_display = ['discussion', 'user', 'is_solution', 'created_at']
    list_filter = ['is_solution']
    search_fields = ['body', 'discussion__title', 'user__username']