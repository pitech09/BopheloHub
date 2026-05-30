from django.urls import path

from certificates.views import certificate_list, certificate_detail, certificate_download

app_name = 'certificates'

urlpatterns = [
    path('certificates/', certificate_list, name='certificates'),
    path('certificate/<int:pk>/', certificate_detail, name='certificate_detail'),
    path('certificate/<int:pk>/download/', certificate_download, name='certificate_download'),
]
