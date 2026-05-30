from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from courses.models import Course
from .models import Review


@login_required
def create_review(request, course_id):
    """Create a review for a course."""
    course = get_object_or_404(Course, pk=course_id, is_published=True)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        if not rating:
            messages.error(request, 'Rating is required.')
            return redirect('course_detail', slug=course.slug)
        
        # Check if user already reviewed this course
        existing_review = Review.objects.filter(user=request.user, course=course).first()
        if existing_review:
            # Update existing review
            existing_review.rating = int(rating)
            existing_review.comment = comment
            existing_review.save()
            messages.success(request, 'Your review has been updated.')
        else:
            # Create new review
            Review.objects.create(
                user=request.user,
                course=course,
                rating=int(rating),
                comment=comment
            )
            messages.success(request, 'Thank you for your review!')
    
    return redirect('course_detail', slug=course.slug)