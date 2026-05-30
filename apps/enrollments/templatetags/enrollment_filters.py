from django import template

register = template.Library()


@register.filter(name='filter_in_progress')
def filter_in_progress(enrollments):
    """Filter enrollments to show only those in progress (not completed, but started)."""
    return enrollments.filter(completed=False, progress__gt=0)


@register.filter(name='filter_completed')
def filter_completed(enrollments):
    """Filter enrollments to show only completed ones."""
    return enrollments.filter(completed=True)