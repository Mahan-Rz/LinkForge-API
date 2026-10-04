from django.urls import path

from .views import (
    DocumentedObtainAuthToken,
    ShortenedURLDetailView,
    ShortenedURLListCreateView,
)

urlpatterns = [
    path(
        'auth/token/',
        DocumentedObtainAuthToken.as_view(),
        name='api-token-auth',
    ),
    path('urls/', ShortenedURLListCreateView.as_view(), name='url-list-create'),
    path('urls/<int:pk>/', ShortenedURLDetailView.as_view(), name='url-detail'),
]