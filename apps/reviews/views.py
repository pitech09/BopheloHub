import json
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from courses.models import Course
from enrollments.models import Enrollment
from .models import Review


@login_required
@require_POST
def create_review(request, course_id):
    """Create or update a review for a course via AJAX."""
    course = get_object_or_404(Course, pk=course_id, is_published=True)

    # Check enrollment
    enrollment = Enrollment.objects.filter(
        user=request.user, course=course, status='active'
    ).exists()
    if not enrollment:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Only enrolled students can review this course.'}, status=403)
        messages.error(request, 'Only enrolled students can review this course.')
        return redirect('course_detail', slug=course.slug)

    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '').strip()

    if not rating:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Rating is required.'}, status=400)
        messages.error(request, 'Rating is required.')
        return redirect('course_detail', slug=course.slug)

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except (ValueError, TypeError):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Rating must be between 1 and 5.'}, status=400)
        messages.error(request, 'Invalid rating.')
        return redirect('course_detail', slug=course.slug)

    existing_review = Review.objects.filter(user=request.user, course=course).first()

    if existing_review:
        existing_review.rating = rating
        existing_review.comment = comment
        existing_review.save()
        message = 'Your review has been updated.'
    else:
        existing_review = Review.objects.create(
            user=request.user,
            course=course,
            rating=rating,
            comment=comment
        )
        message = 'Thank you for your review!'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': message,
            'review': {
                'id': existing_review.pk,
                'rating': existing_review.rating,
                'comment': existing_review.comment,
                'created_at': existing_review.created_at.strftime('%b %d, %Y'),
                'updated_at': existing_review.updated_at.strftime('%b %d, %Y') if existing_review.updated_at else '',
                'user_name': existing_review.user.get_full_name() or existing_review.user.username,
                'user_initials': (existing_review.user.get_full_name() or existing_review.user.username)[0].upper(),
                'has_avatar': bool(existing_review.user.profile_picture),
                'avatar_url': existing_review.user.profile_picture.url if existing_review.user.profile_picture else '',
            }
        })

    messages.success(request, message)
    return redirect('course_detail', slug=course.slug)


@login_required
@require_POST
def delete_review(request, course_id):
    """Delete a review via AJAX."""
    course = get_object_or_404(Course, pk=course_id, is_published=True)
    review = get_object_or_404(Review, user=request.user, course=course)
    review.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Your review has been deleted.'})

    messages.success(request, 'Your review has been deleted.')
    return redirect('course_detail', slug=course.slug)


@login_required
def get_review_data(request, course_id):
    """Return the current user's review data as JSON for editing."""
    course = get_object_or_404(Course, pk=course_id, is_published=True)
    review = Review.objects.filter(user=request.user, course=course).first()

    if review:
        return JsonResponse({
            'has_review': True,
            'review': {
                'id': review.pk,
                'rating': review.rating,
                'comment': review.comment,
            }
        })
    return JsonResponse({'has_review': False})