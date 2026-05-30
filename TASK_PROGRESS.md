# Apple UI Upgrade & Payment/Assessment System

## Implementation Plan

### Phase 1: Backend - Models & Logic
- [x] Update `apps/payments/models.py` - Add screenshot, reference, approval fields
- [ ] Create `apps/payments/forms.py` - Payment with screenshot upload
- [ ] Update `apps/enrollments/models.py` - Add status field (pending/approved/rejected)
- [ ] Create `apps/assessments/` app (models, views, forms, urls)

### Phase 2: Views & URLs
- [ ] Update `apps/courses/views.py` - Payment-based enrollment flow
- [ ] Update `apps/enrollments/views.py` - Handle enrollment approvals
- [ ] Create assessment views (instructor creates, student submits)
- [ ] Update all URL configurations

### Phase 3: Apple-Style CSS
- [ ] Rewrite `static/css/style.css` - Complete Apple design language

### Phase 4: Templates
- [ ] Update `templates/base.html` - Glassmorphism navbar, refined footer
- [ ] Update `templates/home.html` - Apple-style hero & sections
- [ ] Update `templates/courses/course_list.html` - Refined grid
- [ ] Update `templates/courses/course_detail.html` - Apple layout
- [ ] Update `templates/enrollments/student_dashboard.html`
- [ ] Update `templates/courses/instructor_dashboard.html`
- [ ] Update auth templates (login, register)
- [ ] Create payment templates
- [ ] Create assessment templates

### Phase 5: Migrations & Testing
- [ ] Run makemigrations & migrate
- [ ] Verify everything works