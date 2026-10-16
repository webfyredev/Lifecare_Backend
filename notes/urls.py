from django.urls import path
from .views import *

urlpatterns = [
    path('', MedicalNotesView.as_view(), name='medical-notes'),
    path('<int:pk>/', MedicalNotesDetailView.as_view(), name='medical-note-details'),
]