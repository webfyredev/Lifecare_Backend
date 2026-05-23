from django.urls import path
from .views import *

urlpatterns = [
    path('', NotificationListView.as_view(), name='notifications'),
    path('mark-all-read/', MarkAllReadView.as_view(), name='mark-all-read'),
    path('<int:pk>/read/', MarkOneReadView.as_view(), name='mark-one-read')
]
