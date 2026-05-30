from django import template

register = template.Library()


MESSAGE_ICONS = {
    'error': 'exclamation-triangle-fill',
    'success': 'check-circle-fill',
    'info': 'info-circle-fill',
    'warning': 'exclamation-circle-fill',
    'debug': 'bug-fill',
}


@register.filter
def message_icon(tag):
    """Return a Bootstrap Icons class name for the given message tag."""
    return MESSAGE_ICONS.get(tag.lower(), 'info-circle-fill')


@register.filter
def neg(value):
    """Return the negation of a number."""
    try:
        return -int(value)
    except (ValueError, TypeError):
        return 0
