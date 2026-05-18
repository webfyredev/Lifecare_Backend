from django.urls import path
from .views import RegisterView, UserDetailView, LogoutView
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import EmailTokenObtainPairView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', EmailTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', UserDetailView.as_view(), name='user_detail'),
]