from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('review/course/<int:course_id>/', views.create_review, name='create_review'),
    path('review/course/<int:course_id>/delete/', views.delete_review, name='delete_review'),
    path('review/course/<int:course_id>/data/', views.get_review_data, name='get_review_data'),
]