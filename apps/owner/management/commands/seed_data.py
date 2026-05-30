"""
Management command to populate the database with dummy/seed data
for testing the platform owner dashboard and all system features.

Usage:
    python manage.py seed_data                  # Create all seed data
    python manage.py seed_data --flush           # Clear all data first
    python manage.py seed_data --users 20        # Custom user count
"""

import os
import random
import uuid
from datetime import timedelta, datetime
from io import BytesIO

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from PIL import Image
from django.core.files.base import ContentFile

User = get_user_model()

# Import all models
from courses.models import Course, Category
from lessons.models import Section, Lesson
from enrollments.models import Enrollment, LessonCompletion
from payments.models import Payment
from instructors.models import InstructorProfile
from reviews.models import Review
from certificates.models import Certificate
from assessments.models import Assessment, AssessmentQuestion, AssessmentSubmission, SubmissionAnswer
from quizzes.models import Quiz, Question, Choice, UserQuizAttempt
from notifications.models import Notification
from analytics.models import CourseView, LessonView


def generate_photo(color=None):
    """Generate a small placeholder image."""
    if color is None:
        color = tuple(random.randint(50, 200) for _ in range(3))
    img = Image.new('RGB', (200, 150), color)
    buf = BytesIO()
    img.save(buf, 'JPEG', quality=80)
    return ContentFile(buf.getvalue(), name=f'seed_{uuid.uuid4().hex[:8]}.jpg')


class Command(BaseCommand):
    help = 'Seed the database with dummy data for testing the platform owner dashboard.'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Clear all existing data first')
        parser.add_argument('--users', type=int, default=15, help='Number of student users to create')
        parser.add_argument('--courses', type=int, default=8, help='Number of courses to create')

    @transaction.atomic
    def handle(self, *args, **options):
        flush = options['flush']
        user_count = options['users']
        course_count = options['courses']

        if flush:
            self.stdout.write(self.style.WARNING('Flushing all existing data...'))
            self._flush_data()

        self.stdout.write(self.style.NOTICE('Seeding database...'))

        # --- Create Categories ---
        categories = self._create_categories()
        self.stdout.write(f'  ✓ Created {len(categories)} categories')

        # --- Create Users ---
        admin, instructors, students = self._create_users(user_count)
        self.stdout.write(f'  ✓ Created {len(instructors)} instructors, {len(students)} students, 1 admin')

        # --- Create Instructor Profiles ---
        for inst in instructors:
            self._create_instructor_profile(inst)
        self.stdout.write(f'  ✓ Created {len(instructors)} instructor profiles')

        # --- Create Courses ---
        courses = self._create_courses(instructors, categories, course_count)
        self.stdout.write(f'  ✓ Created {len(courses)} courses with sections and lessons')

        # --- Create Enrollments & Payments ---
        enrollments = self._create_enrollments(students, courses)
        self.stdout.write(f'  ✓ Created {len(enrollments)} enrollments')

        payments = self._create_payments(students, courses, enrollments, admin)
        self.stdout.write(f'  ✓ Created {len(payments)} payments')

        # --- Complete some lessons (progress) ---
        self._create_lesson_completions(enrollments)
        self.stdout.write('  ✓ Created lesson completions')

        # --- Create Reviews ---
        reviews = self._create_reviews(students, courses)
        self.stdout.write(f'  ✓ Created {len(reviews)} reviews')

        # --- Create Certificates ---
        certs = self._create_certificates(enrollments)
        self.stdout.write(f'  ✓ Created {len(certs)} certificates')

        # --- Create Assessments ---
        self._create_assessments(courses, enrollments, admin)
        self.stdout.write('  ✓ Created assessments & submissions')

        # --- Create Quizzes ---
        self._create_quizzes(courses, students)
        self.stdout.write('  ✓ Created quizzes & attempts')

        # --- Create Notifications ---
        self._create_notifications(students, instructors)
        self.stdout.write('  ✓ Created notifications')

        # --- Create Analytics ---
        self._create_analytics(students, courses)
        self.stdout.write('  ✓ Created analytics data')

        self.stdout.write(self.style.SUCCESS('\n✅ Database seeding complete!'))
        self._print_credentials(admin, instructors, students)

    def _print_credentials(self, admin, instructors, students):
        """Print all user credentials."""
        admin_password = os.environ.get('SEED_ADMIN_PASSWORD', 'Admin@2026!Secure')
        user_password = self._get_user_password()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('  USER CREDENTIALS'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        self.stdout.write(self.style.WARNING('\n── Admin ──'))
        self.stdout.write(f'  Email:    {admin.email}')
        self.stdout.write(f'  Password: {admin_password}')
        self.stdout.write(f'  Role:     Superuser / Staff')

        self.stdout.write(self.style.WARNING('\n── Instructors ──'))
        for user in instructors:
            self.stdout.write(f'  Email:    {user.email}')
            self.stdout.write(f'  Password: {user_password}')
            self.stdout.write(f'  Name:     {user.get_full_name()}')
            self.stdout.write('')

        self.stdout.write(self.style.WARNING('\n── Students ──'))
        for user in students:
            self.stdout.write(f'  Email:    {user.email}')
            self.stdout.write(f'  Password: {user_password}')
            self.stdout.write(f'  Name:     {user.get_full_name()}')
            self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.NOTICE(
            f'Tip: Override passwords via SEED_ADMIN_PASSWORD and SEED_USER_PASSWORD env vars.'
        ))

    def _flush_data(self):
        """Clear all existing data in correct dependency order."""
        # Delete in reverse dependency order (child tables first)
        models_to_delete = [
            CourseView, LessonView, Notification, UserQuizAttempt,
            Choice, Question, Quiz,
            SubmissionAnswer, AssessmentSubmission,
            AssessmentQuestion, Assessment,
            Certificate, Review, Payment,
            LessonCompletion, Enrollment,
            Lesson, Section,
            Course, InstructorProfile, Category,
        ]
        for m in models_to_delete:
            m.objects.all().delete()
        # Remove non-core users
        User.objects.filter(is_superuser=False).delete()
        User.objects.filter(is_superuser=True).exclude(email='admin@learnhub.com').delete()

    def _create_categories(self):
        names = [
            ('Web Development', 'web-development'),
            ('Data Science', 'data-science'),
            ('Mobile Development', 'mobile-development'),
            ('DevOps & Cloud', 'devops-cloud'),
            ('Design & UX', 'design-ux'),
            ('Business & Marketing', 'business-marketing'),
        ]
        categories = []
        for name, slug in names:
            cat, _ = Category.objects.get_or_create(name=name, slug=slug)
            categories.append(cat)
        return categories

    def _create_users(self, student_count):
        # Admin
        admin, _ = User.objects.get_or_create(
            email='admin@learnhub.com',
            defaults={
                'username': 'admin',
                'first_name': 'Platform',
                'last_name': 'Admin',
                'is_superuser': True,
                'is_staff': True,
            }
        )
        admin_password = os.environ.get('SEED_ADMIN_PASSWORD', 'Admin@2026!Secure')
        admin.set_password(admin_password)
        admin.save()

        # Instructors (5)
        instructor_data = [
            ('john.doe@example.com', 'John', 'Doe'),
            ('jane.smith@example.com', 'Jane', 'Smith'),
            ('bob.wilson@example.com', 'Bob', 'Wilson'),
            ('alice.johnson@example.com', 'Alice', 'Johnson'),
            ('mike.brown@example.com', 'Mike', 'Brown'),
        ]
        instructors = []
        for email, first, last in instructor_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': first,
                    'last_name': last,
                    'is_instructor': True,
                }
            )
            if created:
                user.set_password(self._get_user_password())
                user.save()
            instructors.append(user)

        # Additional pending instructors
        pending_data = [
            ('sarah.lee@example.com', 'Sarah', 'Lee'),
            ('tom.garcia@example.com', 'Tom', 'Garcia'),
        ]
        for email, first, last in pending_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': first,
                    'last_name': last,
                    'is_instructor': False,
                }
            )
            if created:
                user.set_password(self._get_user_password())
                user.save()
            # Create a pending instructor profile
            InstructorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'headline': f'Aspiring {random.choice(["Web Developer", "Data Scientist", "Designer", "DevOps Engineer"])}',
                    'qualifications': 'Certified professional with 3+ years of industry experience.',
                    'status': 'pending',
                }
            )

        # Students
        students = []
        first_names = ['Emma', 'Liam', 'Olivia', 'Noah', 'Ava', 'Ethan', 'Sophia', 'Mason',
                      'Isabella', 'Logan', 'Mia', 'Lucas', 'Charlotte', 'James', 'Amelia',
                      'Benjamin', 'Harper', 'Elijah', 'Evelyn', 'Alexander']
        last_names = ['Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
                     'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson',
                     'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee']
        for i in range(student_count):
            first = random.choice(first_names)
            last = random.choice(last_names)
            email = f'{first.lower()}.{last.lower()}{i}@example.com'
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': f'{first.lower()}{last.lower()}{i}',
                    'first_name': first,
                    'last_name': last,
                }
            )
            if created:
                user.set_password(self._get_user_password())
                user.save()
            students.append(user)

        return admin, instructors, students

    def _get_user_password(self):
        """Return a non-trivial default password (override via env)."""
        return os.environ.get(
            'SEED_USER_PASSWORD',
            'LearnHub@2026!'
        )

    def _create_instructor_profile(self, user):
        headlines = [
            'Full-Stack Developer with 10+ years experience',
            'Data Scientist at Google | ML Engineer',
            'Senior UI/UX Designer | Design Thinking Advocate',
            'DevOps Engineer | AWS Certified Solutions Architect',
            'Python & Django Expert | Open Source Contributor',
        ]
        qualifications = [
            'MSc Computer Science, Stanford University',
            'BSc Software Engineering, MIT',
            'PhD Artificial Intelligence, Cambridge',
            'Certified Kubernetes Administrator',
            'AWS Certified Solutions Architect',
        ]
        InstructorProfile.objects.get_or_create(
            user=user,
            defaults={
                'headline': random.choice(headlines),
                'website': f'https://{user.username}.dev',
                'phone': f'+266{random.randint(50000000, 59999999)}',
                'qualifications': random.choice(qualifications),
                'status': 'verified',
            }
        )

    def _create_courses(self, instructors, categories, count):
        course_templates = [
            ('Python for Beginners', 'Learn Python from scratch. Master variables, functions, OOP, and build real-world projects.', 49.99),
            ('Advanced Django Web Development', 'Build production-ready web applications with Django, DRF, and modern tools.', 79.99),
            ('React & Next.js Masterclass', 'Modern frontend development with React hooks, context, Next.js, and TypeScript.', 69.99),
            ('Machine Learning with Python', 'ML algorithms, scikit-learn, TensorFlow, and real-world data science projects.', 89.99),
            ('Docker & Kubernetes Deep Dive', 'Containerization, orchestration, CI/CD pipelines, and cloud deployment.', 74.99),
            ('UI-UX Design Fundamentals', 'Design thinking, wireframing, prototyping with Figma, and user research.', 59.99),
            ('Full-Stack JavaScript', 'Node.js, Express, MongoDB, React, and deployment. Build complete web apps.', 64.99),
            ('Data Analysis with Pandas', 'Data cleaning, visualization, statistical analysis, and business intelligence.', 54.99),
            ('AWS Cloud Architecture', 'EC2, S3, Lambda, RDS, VPC, and designing scalable cloud solutions.', 84.99),
            ('Mobile Apps with Flutter', 'Cross-platform mobile development with Dart and Flutter framework.', 69.99),
        ]
        courses = []
        for i in range(min(count, len(course_templates))):
            title, desc, price = course_templates[i]
            instructor = random.choice(instructors)
            category = random.choice(categories)
            slug = title.lower().replace(' ', '-').replace('&', 'and').replace('.', '-')

            course, created = Course.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'instructor': instructor,
                    'category': category,
                    'description': f'<p>{desc}</p>',
                    'price': price,
                    'is_published': random.random() > 0.2,  # 80% published
                }
            )
            if created:
                # Assign thumbnail
                course.thumbnail.save(
                    f'{slug}.jpg',
                    generate_photo(color=(random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))),
                    save=True
                )

            # Create sections & lessons
            section_count = random.randint(2, 4)
            for s_idx in range(1, section_count + 1):
                section, _ = Section.objects.get_or_create(
                    course=course,
                    order=s_idx,
                    defaults={'title': f'{["Getting Started", "Core Concepts", "Advanced Topics", "Projects & Practice"][s_idx - 1]}'}
                )
                lesson_count = random.randint(2, 4)
                for l_idx in range(1, lesson_count + 1):
                    Lesson.objects.get_or_create(
                        section=section,
                        order=l_idx,
                        defaults={
                            'title': f'Lesson {l_idx}: {"Introduction" if l_idx == 1 else "Deep Dive" if l_idx == 2 else "Hands-On" if l_idx == 3 else "Summary"}',
                            'content': f'<h3>Lesson Content</h3><p>This is the content for lesson {l_idx} in {section.title}.</p><p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>',
                            'video_url': 'https://www.youtube.com/embed/dQw4w9WgXcQ',
                        }
                    )

            courses.append(course)
        return courses

    def _create_enrollments(self, students, courses):
        enrollments = []
        statuses = ['active', 'active', 'active', 'pending', 'rejected']  # weighted
        for student in students:
            enrolled_courses = random.sample(courses, random.randint(1, min(4, len(courses))))
            for course in enrolled_courses:
                status = random.choice(statuses)
                enrollment, created = Enrollment.objects.get_or_create(
                    user=student,
                    course=course,
                    defaults={
                        'status': status,
                        'enrolled_at': timezone.now() - timedelta(days=random.randint(1, 60)),
                    }
                )
                if created:
                    enrollments.append(enrollment)
        return enrollments

    def _create_payments(self, students, courses, enrollments, admin):
        payments = []
        statuses = ['verified', 'verified', 'verified', 'pending', 'rejected']
        for enrollment in enrollments:
            if enrollment.status == 'pending':
                status = 'pending'
            elif enrollment.status == 'active':
                status = 'verified'
            else:
                status = 'rejected'

            ref = f'PAY-{uuid.uuid4().hex[:8].upper()}'
            payment, created = Payment.objects.get_or_create(
                user=enrollment.user,
                course=enrollment.course,
                reference_number=ref,
                defaults={
                    'amount': enrollment.course.price,
                    'status': status,
                    'paid_at': enrollment.enrolled_at,
                    'verified_at': enrollment.enrolled_at + timedelta(hours=random.randint(1, 48)) if status == 'verified' else None,
                    'verified_by': admin if status == 'verified' else None,
                }
            )
            if created and status != 'verified':
                # Still need a reference/amount
                payment.amount = enrollment.course.price
                payment.save()
            if created:
                # Attach a dummy screenshot
                buf = BytesIO()
                img = Image.new('RGB', (500, 300), (200, 230, 255))
                img.save(buf, 'JPEG', quality=70)
                payment.screenshot.save(
                    f'payment_{ref}.jpg',
                    ContentFile(buf.getvalue()),
                    save=True
                )
                payments.append(payment)
        return payments

    def _create_lesson_completions(self, enrollments):
        """Mark some lessons as completed for active enrollments."""
        for enrollment in enrollments:
            if enrollment.status != 'active':
                continue
            lessons = Lesson.objects.filter(section__course=enrollment.course)
            completed = random.sample(list(lessons), min(random.randint(1, lessons.count()), max(1, lessons.count() // 2)))
            for lesson in completed:
                LessonCompletion.objects.get_or_create(
                    enrollment=enrollment,
                    lesson=lesson,
                    defaults={'completed_at': timezone.now() - timedelta(days=random.randint(0, 30))}
                )
            # Update progress
            enrollment.calculate_progress()

    def _create_reviews(self, students, courses):
        reviews = []
        comments = [
            'Excellent course! Very well structured and easy to follow.',
            'Great content, but could use more practical examples.',
            'Loved the teaching style. Highly recommended!',
            'Good course for beginners. The instructor explains concepts clearly.',
            'The projects were very helpful for understanding real-world applications.',
            'Average course. Some sections felt rushed.',
            'Outstanding! Best course I have taken on this platform.',
            'Informative and engaging. The assignments were challenging but rewarding.',
            'I learned a lot. Will definitely check out other courses from this instructor.',
            'Perfect pace for working professionals. Thank you!',
        ]
        for student in students:
            enrolled = Enrollment.objects.filter(user=student, status='active')
            for e in enrolled:
                if random.random() > 0.6:  # 40% chance to leave a review
                    review, created = Review.objects.get_or_create(
                        user=student,
                        course=e.course,
                        defaults={
                            'rating': random.randint(3, 5),
                            'comment': random.choice(comments),
                        }
                    )
                    if created:
                        reviews.append(review)
        return reviews

    def _create_certificates(self, enrollments):
        """Create certificates for completed enrollments."""
        certs = []
        for enrollment in enrollments:
            if enrollment.completed or (enrollment.status == 'active' and enrollment.progress >= 100):
                cert, created = Certificate.objects.get_or_create(
                    enrollment=enrollment,
                    defaults={
                        'certificate_code': f'CERT-{uuid.uuid4().hex[:12].upper()}',
                        'issued_at': timezone.now() - timedelta(days=random.randint(0, 15)),
                    }
                )
                if created:
                    certs.append(cert)
        return certs

    def _create_assessments(self, courses, enrollments, admin):
        assessment_titles = [
            'Mid-Term Assessment', 'Final Project', 'Module 1 Quiz',
            'Practical Exam', 'Knowledge Check',
        ]
        for course in courses[:5]:  # Create for first 5 courses
            title = random.choice(assessment_titles)
            assessment, created = Assessment.objects.get_or_create(
                course=course,
                title=f'{title} - {course.title}',
                defaults={
                    'description': f'Assessment for {course.title} to test your understanding.',
                    'due_date': timezone.now() + timedelta(days=random.randint(5, 30)),
                    'total_points': 100,
                }
            )
            if not created:
                continue

            # Create questions
            for q_idx in range(1, 4):
                q_type = random.choice(['multiple_choice', 'essay'])
                question = AssessmentQuestion.objects.create(
                    assessment=assessment,
                    question_text=f'Question {q_idx}: {"What is the correct approach?" if q_type == "multiple_choice" else "Explain the concept in detail."}',
                    question_type=q_type,
                    points=random.choice([10, 15, 20]),
                    order=q_idx,
                    option_a='Option A' if q_type == 'multiple_choice' else '',
                    option_b='Option B' if q_type == 'multiple_choice' else '',
                    option_c='Option C' if q_type == 'multiple_choice' else '',
                    option_d='Option D' if q_type == 'multiple_choice' else '',
                    correct_answer='A' if q_type == 'multiple_choice' else '',
                )

            # Create submissions
            course_enrollments = [e for e in enrollments if e.course_id == course.id and e.status == 'active']
            for e in course_enrollments[:3]:
                sub, _ = AssessmentSubmission.objects.get_or_create(
                    assessment=assessment,
                    enrollment=e,
                    defaults={
                        'submitted_at': timezone.now() - timedelta(days=random.randint(0, 5)),
                        'graded': random.random() > 0.3,
                        'score': random.randint(50, 100) if random.random() > 0.3 else None,
                        'feedback': 'Great work! Keep it up.' if random.random() > 0.5 else 'Good attempt. Review the course material.',
                        'graded_by': admin if random.random() > 0.3 else None,
                        'graded_at': timezone.now() - timedelta(days=random.randint(0, 2)) if random.random() > 0.3 else None,
                    }
                )

    def _create_quizzes(self, courses, students):
        for course in courses[:4]:
            lessons = Lesson.objects.filter(section__course=course)[:2]
            for lesson in lessons:
                quiz, created = Quiz.objects.get_or_create(
                    lesson=lesson,
                    defaults={
                        'title': f'Quiz: {lesson.title}',
                        'pass_percentage': 70,
                    }
                )
                if not created:
                    continue

                # Add questions
                for q_idx in range(1, 4):
                    question = Question.objects.create(
                        quiz=quiz,
                        text=f'Question {q_idx}: What is the correct answer about {lesson.title}?',
                        order=q_idx,
                    )
                    # Add choices
                    choices = [
                        ('Correct answer description', True),
                        ('Wrong option 1', False),
                        ('Wrong option 2', False),
                        ('Wrong option 3', False),
                    ]
                    random.shuffle(choices)
                    for text, is_correct in choices:
                        Choice.objects.create(
                            question=question,
                            text=text,
                            is_correct=is_correct,
                        )

                # Create attempts
                enrolled_students = Enrollment.objects.filter(course=course, status='active')[:3]
                for e in enrolled_students:
                    score = random.randint(40, 100)
                    UserQuizAttempt.objects.create(
                        user=e.user,
                        quiz=quiz,
                        score=score,
                        passed=score >= quiz.pass_percentage,
                    )

    def _create_notifications(self, students, instructors):
        messages = [
            'Welcome to LearnHub! Start learning today.',
            'Your course has been published successfully!',
            'New course recommendations available for you.',
            'You have a new message from your instructor.',
            'Don\'t forget to complete your ongoing courses!',
            'A new certificate is available for download.',
            'Your payment has been verified successfully.',
            'Course enrollment approved! Start learning now.',
        ]
        for user in students[:10]:
            Notification.objects.get_or_create(
                user=user,
                message=random.choice(messages),
                defaults={
                    'is_read': random.random() > 0.5,
                    'created_at': timezone.now() - timedelta(days=random.randint(0, 7)),
                }
            )
        for user in instructors:
            Notification.objects.get_or_create(
                user=user,
                message='A new student has enrolled in your course.',
                defaults={
                    'is_read': random.random() > 0.4,
                    'created_at': timezone.now() - timedelta(days=random.randint(0, 5)),
                }
            )

    def _create_analytics(self, students, courses):
        for course in courses:
            for _ in range(random.randint(3, 10)):
                user = random.choice(students[:10]) if random.random() > 0.3 else None
                CourseView.objects.create(
                    user=user,
                    course=course,
                    viewed_at=timezone.now() - timedelta(days=random.randint(0, 30)),
                )
            # Lesson views
            lessons = Lesson.objects.filter(section__course=course)[:3]
            for lesson in lessons:
                for _ in range(random.randint(2, 5)):
                    user = random.choice(students[:10]) if random.random() > 0.3 else None
                    LessonView.objects.create(
                        user=user,
                        lesson=lesson,
                        viewed_at=timezone.now() - timedelta(days=random.randint(0, 30)),
                    )