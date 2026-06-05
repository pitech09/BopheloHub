from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'reference_number', 'user', 'course', 'amount_display',
        'status_badge', 'paid_at', 'verified_at', 'verified_by'
    ]
    list_filter = ['status', 'paid_at', 'verified_at']
    search_fields = [
        'reference_number', 'user__email', 'user__username',
        'course__title', 'admin_note'
    ]
    readonly_fields = ['reference_number', 'paid_at', 'paid_at']
    list_per_page = 25
    date_hierarchy = 'paid_at'
    ordering = ['-paid_at']

    fieldsets = (
        ('Payment Info', {
            'fields': ('reference_number', 'user', 'course', 'amount', 'screenshot')
        }),
        ('Status', {
            'fields': ('status', 'admin_note')
        }),
        ('Verification', {
            'fields': ('verified_at', 'verified_by'),
            'classes': ('collapse',)
        }),
    )

    def amount_display(self, obj):
        return f"M{obj.amount:.2f}"
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def status_badge(self, obj):
        colors = {
            'pending': 'bg-warning text-dark',
            'verified': 'bg-success',
            'rejected': 'bg-danger',
        }
        color = colors.get(obj.status, 'bg-secondary')
        return f'<span class="badge {color}">{obj.get_status_display()}</span>'
    status_badge.short_description = 'Status'
    status_badge.allow_tags = True

    actions = ['mark_as_verified', 'mark_as_rejected']

    def mark_as_verified(self, request, queryset):
        from django.utils import timezone
        from notifications.models import Notification
        from enrollments.models import Enrollment

        updated = queryset.filter(status='pending').update(
            status='verified',
            verified_by=request.user,
            verified_at=timezone.now()
        )

        # Activate associated enrollments
        for payment in queryset.filter(status='verified'):
            enrollment = Enrollment.objects.filter(
                user=payment.user, course=payment.course, status='pending'
            ).first()
            if enrollment:
                enrollment.status = 'active'
                enrollment.save()

            Notification.objects.create(
                user=payment.user,
                message=f'Your payment of M{payment.amount} for "{payment.course.title}" has been verified!'
            )

        self.message_user(request, f'{updated} payment(s) marked as verified.')
    mark_as_verified.short_description = 'Mark selected payments as verified'

    def mark_as_rejected(self, request, queryset):
        from notifications.models import Notification
        from enrollments.models import Enrollment

        updated = queryset.filter(status='pending').update(status='rejected')

        for payment in queryset.filter(status='rejected'):
            enrollment = Enrollment.objects.filter(
                user=payment.user, course=payment.course, status='pending'
            ).first()
            if enrollment:
                enrollment.status = 'rejected'
                enrollment.save()

            Notification.objects.create(
                user=payment.user,
                message=f'Your payment of M{payment.amount} for "{payment.course.title}" has been rejected.'
            )

        self.message_user(request, f'{updated} payment(s) marked as rejected.')
    mark_as_rejected.short_description = 'Mark selected payments as rejected'