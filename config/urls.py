from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('', include('courses.urls')),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('lessons.urls')),
    path('', include('enrollments.urls')),
    path('', include('reviews.urls')),
    path('', include('certificates.urls')),
    path('', include('assessments.urls')),
    path('', include('owner.urls')),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
