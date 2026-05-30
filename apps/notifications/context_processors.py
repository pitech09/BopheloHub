from django.db.models import Q


def notifications(request):
    """
    Context processor to add notification data to all templates.
    """
    if not request.user.is_authenticated:
        return {
            'unread_notifications': 0,
            'recent_notifications': [],
        }
    
    from .models import Notification
    
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    recent_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    return {
        'unread_notifications': unread_count,
        'recent_notifications': recent_notifications,
    }