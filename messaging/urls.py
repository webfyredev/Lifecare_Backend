from django.urls import path
from .views import *

urlpatterns = [
    path('', ConversationListView.as_view(), name='conversations'),
    path('<int:conv_id>/messages/', MessageListView.as_view(), name='messages'),
    path('<int:conv_id>/messages/<int:message_id>/', MessageDetailView.as_view(), name='message-detail')
]
