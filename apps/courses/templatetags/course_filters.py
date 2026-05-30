from django import template

register = template.Library()


@register.filter(name='rating_count')
def rating_count(course, rating_value):
    """Get the count of reviews with a specific rating for a course."""
    try:
        rating_value = int(rating_value)
    except (ValueError, TypeError):
        return 0
    
    if not hasattr(course, 'reviews'):
        return 0
    
    return course.reviews.filter(rating=rating_value).count()


@register.filter(name='rating_percentage')
def rating_percentage(course, rating_value):
    """Get the percentage of reviews with a specific rating for a course."""
    try:
        rating_value = int(rating_value)
    except (ValueError, TypeError):
        return 0
    
    if not hasattr(course, 'reviews'):
        return 0
    
    total_reviews = course.reviews.count()
    if total_reviews == 0:
        return 0
    
    rating_count = course.reviews.filter(rating=rating_value).count()
    return round((rating_count / total_reviews) * 100)