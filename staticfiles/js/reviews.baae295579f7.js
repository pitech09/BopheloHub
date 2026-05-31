/**
 * BopheloHub Reviews - Apple-Inspired Premium Interactive Reviews
 * Handles star rating, form submission, edit/delete, animations, and toasts
 */

document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    // ============================================
    // Rating Distribution Bar Animation with Spring Physics
    // ============================================
    function animateRatingBars() {
        const bars = document.querySelectorAll('.rating-dist-bar-fill');
        bars.forEach(function(bar, index) {
            const targetWidth = bar.getAttribute('data-width') || '0';
            setTimeout(function() {
                bar.style.width = targetWidth + '%';
                bar.classList.add('animated');
            }, 150 + (index * 80));
        });
    }

    // Intersection Observer for bars (animate when scrolled into view)
    const overviewCard = document.querySelector('.reviews-overview-card');
    if (overviewCard) {
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    animateRatingBars();
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.25 });
        observer.observe(overviewCard);
    } else {
        // Fallback: animate on load
        setTimeout(animateRatingBars, 400);
    }

    // ============================================
    // Interactive Star Rating (Apple Spring Animation)
    // ============================================
    const starLabels = document.querySelectorAll('.star-rating-input:not(.readonly) label');
    const starInputs = document.querySelectorAll('.star-rating-input input');
    const ratingLabelText = document.querySelector('.rating-label-text');

    const ratingLabels = {
        5: 'Excellent! \u2605\u2605\u2605\u2605\u2605',
        4: 'Great \u2605\u2605\u2605\u2605',
        3: 'Good \u2605\u2605\u2605',
        2: 'Fair \u2605\u2605',
        1: 'Poor \u2605'
    };

    const ratingShortLabels = {
        5: 'Excellent!',
        4: 'Great',
        3: 'Good',
        2: 'Fair',
        1: 'Poor'
    };

    starLabels.forEach(function(label) {
        label.addEventListener('mouseenter', function() {
            if (this.closest('.readonly')) return;
            const input = document.querySelector('#' + this.getAttribute('for'));
            if (input) {
                const val = parseInt(input.value);
                if (ratingLabelText && ratingShortLabels[val]) {
                    ratingLabelText.textContent = ratingShortLabels[val];
                }
                // Add hover glow to all stars up to this one
                const allLabels = this.closest('.star-rating-input').querySelectorAll('label');
                allLabels.forEach(function(l) { l.classList.remove('hover-glow'); });
                let reached = false;
                allLabels.forEach(function(l) {
                    if (l === label) reached = true;
                    if (!reached) l.classList.add('hover-glow');
                });
            }
        });

        label.addEventListener('mouseleave', function() {
            if (this.closest('.readonly')) return;
            const container = this.closest('.star-rating-input');
            if (container) {
                container.querySelectorAll('label').forEach(function(l) {
                    l.classList.remove('hover-glow');
                });
            }
            const checkedInput = document.querySelector('.star-rating-input input:checked');
            if (ratingLabelText) {
                if (checkedInput && ratingShortLabels[parseInt(checkedInput.value)]) {
                    ratingLabelText.textContent = ratingShortLabels[parseInt(checkedInput.value)];
                } else {
                    ratingLabelText.textContent = 'Click to rate';
                }
            }
        });
    });

    starInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            const val = parseInt(this.value);
            if (ratingLabelText) {
                if (ratingLabels[val]) {
                    ratingLabelText.textContent = ratingLabels[val];
                } else {
                    ratingLabelText.textContent = 'Click to rate';
                }
            }
            // Trigger spring animation on the container
            const container = this.closest('.star-rating-input');
            if (container) {
                container.classList.remove('rating-selected');
                void container.offsetWidth;
                container.classList.add('rating-selected');
            }
        });
    });

    // Set initial label
    const checkedStar = document.querySelector('.star-rating-input input:checked');
    if (ratingLabelText) {
        if (checkedStar && ratingLabels[parseInt(checkedStar.value)]) {
            ratingLabelText.textContent = ratingLabels[parseInt(checkedStar.value)];
        } else {
            ratingLabelText.textContent = 'Click to rate';
        }
    }

    // ============================================
    // Character Counter with Progress Ring
    // ============================================
    const reviewTextarea = document.querySelector('.review-textarea');
    const charCounter = document.querySelector('.char-counter');

    if (reviewTextarea && charCounter) {
        const maxChars = parseInt(reviewTextarea.getAttribute('maxlength')) || 2000;

        function updateCharCounter() {
            const currentLength = reviewTextarea.value.length;
            const remaining = maxChars - currentLength;
            const percent = (currentLength / maxChars) * 100;

            charCounter.textContent = remaining + ' characters remaining';

            // Update progress ring visual
            charCounter.classList.remove('warning', 'danger');
            if (remaining < 50) {
                charCounter.classList.add('danger');
            } else if (remaining < 200) {
                charCounter.classList.add('warning');
            }

            // Add progress ring indicator
            let ring = charCounter.querySelector('.char-progress-ring');
            if (!ring) {
                ring = document.createElement('span');
                ring.className = 'char-progress-ring';
                charCounter.appendChild(ring);
            }
            ring.classList.toggle('filled', currentLength > 0);
        }

        reviewTextarea.addEventListener('input', updateCharCounter);
        updateCharCounter();
    }

    // ============================================
    // Review Form Submission (AJAX with Premium Loading)
    // ============================================
    const reviewForm = document.querySelector('.review-form-card form');
    if (reviewForm) {
        const submitBtn = reviewForm.querySelector('.review-submit-btn');
        const btnText = submitBtn ? submitBtn.querySelector('.btn-text') : null;
        const btnSpinner = submitBtn ? submitBtn.querySelector('.btn-spinner') : null;

        // Store original button text
        if (submitBtn && !submitBtn.getAttribute('data-original-text')) {
            submitBtn.setAttribute('data-original-text', btnText ? btnText.textContent : 'Submit Review');
        }

        reviewForm.addEventListener('submit', function(e) {
            // Only intercept if it's an AJAX-capable form
            if (!this.getAttribute('data-ajax')) return;
            e.preventDefault();

            const formData = new FormData(this);

            // Validate rating
            const rating = formData.get('rating');
            if (!rating) {
                showToast('Please select a rating before submitting.', 'error');
                // Shake the star rating container
                const starContainer = document.querySelector('.star-rating-input');
                if (starContainer) {
                    starContainer.classList.add('shake-animation');
                    setTimeout(function() {
                        starContainer.classList.remove('shake-animation');
                    }, 600);
                }
                return;
            }

            // Show loading state
            if (submitBtn) {
                submitBtn.disabled = true;
                if (btnText) btnText.textContent = 'Submitting...';
                if (btnSpinner) btnSpinner.classList.remove('d-none');
            }

            fetch(this.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                },
                body: formData
            })
            .then(function(response) {
                return response.json().then(function(data) {
                    if (!response.ok) {
                        throw { status: response.status, data: data };
                    }
                    return data;
                });
            })
            .then(function(data) {
                if (data.success) {
                    showToast(data.message, 'success');
                    // Reload reviews to show updated list
                    setTimeout(function() {
                        window.location.reload();
                    }, 1200);
                } else {
                    showToast(data.error || 'An error occurred.', 'error');
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        if (btnText) btnText.textContent = submitBtn.getAttribute('data-original-text') || 'Submit Review';
                        if (btnSpinner) btnSpinner.classList.add('d-none');
                    }
                }
            })
            .catch(function(err) {
                var errorMsg = 'An error occurred. Please try again.';
                if (err && err.data && err.data.error) {
                    errorMsg = err.data.error;
                }
                showToast(errorMsg, 'error');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    if (btnText) btnText.textContent = submitBtn.getAttribute('data-original-text') || 'Submit Review';
                    if (btnSpinner) btnSpinner.classList.add('d-none');
                }
            });
        });
    }

    // ============================================
    // Delete Review with Confirmation Modal
    // ============================================
    const deleteForm = document.querySelector('#deleteReviewForm');
    const confirmDeleteBtn = document.querySelector('#confirmDeleteBtn');
    // Also support delete links that trigger modal
    const deleteLinks = document.querySelectorAll('.review-delete-link');

    // Wire up delete links to open modal
    deleteLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const modalEl = document.getElementById('deleteReviewModal');
            if (modalEl) {
                const modal = new bootstrap.Modal(modalEl);
                modal.show();
            }
        });
    });

    if (deleteForm && confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function() {
            const formData = new FormData(deleteForm);

            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Deleting...';

            fetch(deleteForm.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                },
                body: formData
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    // Close modal
                    var deleteModalEl = document.getElementById('deleteReviewModal');
                    var deleteModal = bootstrap.Modal.getInstance(deleteModalEl);
                    if (deleteModal) deleteModal.hide();

                    showToast(data.message, 'success');
                    setTimeout(function() {
                        window.location.reload();
                    }, 1200);
                } else {
                    showToast(data.error || 'An error occurred.', 'error');
                    this.disabled = false;
                    this.innerHTML = 'Delete Review';
                }
            })
            .catch(function() {
                showToast('An error occurred. Please try again.', 'error');
                confirmDeleteBtn.disabled = false;
                confirmDeleteBtn.innerHTML = 'Delete Review';
            });
        });
    }

    // ============================================
    // Edit Review - Load existing data into form with smooth scroll
    // ============================================
    const editReviewBtn = document.querySelector('.edit-review-btn');
    if (editReviewBtn) {
        editReviewBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const reviewId = this.getAttribute('data-review-id');
            const url = this.getAttribute('data-url');

            // Show loading state on button
            const originalHtml = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Loading...';
            this.disabled = true;

            fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.has_review) {
                    const review = data.review;
                    // Check the corresponding star
                    const starInput = document.querySelector('.star-rating-input input[value="' + review.rating + '"]');
                    if (starInput) {
                        starInput.checked = true;
                        // Trigger change event
                        var event = new Event('change', { bubbles: true });
                        starInput.dispatchEvent(event);
                    }

                    // Fill textarea
                    if (reviewTextarea) {
                        reviewTextarea.value = review.comment;
                        var inputEvent = new Event('input', { bubbles: true });
                        reviewTextarea.dispatchEvent(inputEvent);
                    }

                    // Update form action if needed
                    if (reviewForm) {
                        // Ensure rating is set in hidden field if exists
                        var ratingHidden = reviewForm.querySelector('input[name="rating"]:not([type="radio"])');
                        if (ratingHidden) {
                            ratingHidden.value = review.rating;
                        }
                    }

                    // Update submit button text
                    if (submitBtn) {
                        submitBtn.setAttribute('data-original-text', 'Update Review');
                        if (btnText) btnText.textContent = 'Update Review';
                    }

                    // Update form title
                    const formTitle = document.querySelector('.review-form-title');
                    if (formTitle) {
                        formTitle.innerHTML = '<i class="bi bi-pencil-square me-2"></i>Edit Your Review';
                    }

                    // Smooth scroll to form
                    const formCard = document.querySelector('.review-form-card');
                    if (formCard) {
                        formCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        // Highlight the form card briefly
                        formCard.classList.add('highlight-flash');
                        setTimeout(function() {
                            formCard.classList.remove('highlight-flash');
                        }, 1500);
                    }

                    // Reset edit button
                    if (editReviewBtn) {
                        editReviewBtn.innerHTML = originalHtml;
                        editReviewBtn.disabled = false;
                    }
                }
            })
            .catch(function() {
                showToast('Could not load your review data.', 'error');
                if (editReviewBtn) {
                    editReviewBtn.innerHTML = originalHtml;
                    editReviewBtn.disabled = false;
                }
            });
        });
    }

    // ============================================
    // Toast Notification (Apple-style)
    // ============================================
    function showToast(message, type) {
        type = type || 'success';
        // Remove existing toast
        var existingToast = document.querySelector('.review-toast');
        if (existingToast) {
            existingToast.remove();
        }

        var toast = document.createElement('div');
        toast.className = 'review-toast ' + type;
        toast.textContent = message;
        document.body.appendChild(toast);

        // Trigger reflow for animation
        void toast.offsetWidth;
        toast.classList.add('show');

        // Auto-dismiss
        setTimeout(function() {
            toast.classList.remove('show');
            setTimeout(function() {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 450);
        }, 3200);
    }

    // Expose showToast globally for inline usage
    window.showReviewToast = showToast;

    // ============================================
    // Fade-in animation for review cards on scroll
    // (Intersection Observer for paused animations)
    // ============================================
    const reviewCards = document.querySelectorAll('.review-card-modern');
    if (reviewCards.length > 0 && 'IntersectionObserver' in window) {
        const cardObserver = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.style.animationPlayState = 'running';
                    cardObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08 });

        reviewCards.forEach(function(card) {
            // Pause animation until visible
            card.style.animationPlayState = 'paused';
            cardObserver.observe(card);
        });
    } else if (reviewCards.length > 0) {
        // Fallback: run all animations
        reviewCards.forEach(function(card) {
            card.style.animationPlayState = 'running';
        });
    }

    // ============================================
    // Star hover animation enhancement (desktop spring)
    // ============================================
    const formStars = document.querySelectorAll('.star-rating-input:not(.readonly) label');
    formStars.forEach(function(star) {
        star.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.22) rotate(-6deg)';
            this.style.transition = 'transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)';
        });
        star.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.transition = '';
        });
    });

    // ============================================
    // Keyboard accessibility for star rating
    // ============================================
    const starRatingContainer = document.querySelector('.star-rating-input:not(.readonly)');
    if (starRatingContainer) {
        starRatingContainer.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
                e.preventDefault();
                const checked = this.querySelector('input:checked');
                if (checked) {
                    const next = checked.nextElementSibling;
                    if (next && next.tagName === 'INPUT') {
                        next.checked = true;
                        var event = new Event('change', { bubbles: true });
                        next.dispatchEvent(event);
                    }
                } else {
                    const first = this.querySelector('input');
                    if (first) {
                        first.checked = true;
                        var event = new Event('change', { bubbles: true });
                        first.dispatchEvent(event);
                    }
                }
            } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
                e.preventDefault();
                const checked = this.querySelector('input:checked');
                if (checked) {
                    const prev = checked.previousElementSibling;
                    if (prev && prev.tagName === 'INPUT') {
                        prev.checked = true;
                        var event = new Event('change', { bubbles: true });
                        prev.dispatchEvent(event);
                    }
                }
            }
        });
    }

    console.log('Apple Reviews module initialized.');
});