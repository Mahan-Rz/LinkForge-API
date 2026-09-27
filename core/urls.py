from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import ShortenedURLDetailView, ShortenedURLListCreateView

urlpatterns = [
    path('auth/token/', obtain_auth_token, name='api-token-auth'),
    path('urls/', ShortenedURLListCreateView.as_view(), name='url-list-create'),
    path('urls/<int:pk>/', ShortenedURLDetailView.as_view(), name='url-detail'),
]