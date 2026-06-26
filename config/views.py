from django.http import HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    """Lightweight health endpoint for cron and uptime checks."""
    return HttpResponse("ok", content_type="text/plain")
