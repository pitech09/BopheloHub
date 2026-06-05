from django import template

register = template.Library()


@register.filter
def dict_key(d, key):
    """Return the value for the given key in a dictionary."""
    if isinstance(d, dict):
        return d.get(key)
    return None