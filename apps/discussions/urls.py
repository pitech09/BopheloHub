from django.urls import path
from . import views

app_name = 'discussions'

urlpatterns = [
    path('course/<slug:slug>/', views.CourseDiscussionListView.as_view(), name='course_discussions'),
    path('course/<slug:slug>/create/', views.create_discussion, name='create_discussion'),
    path('<int:pk>/', views.DiscussionDetailView.as_view(), name='discussion_detail'),
    path('<int:pk>/reply/', views.reply_to_discussion, name='reply_discussion'),
]