from django.urls import path

from .views import ShortenedURLDetailView, ShortenedURLListCreateView

urlpatterns = [
    path('urls/', ShortenedURLListCreateView.as_view(), name='url-list-create'),
    path('urls/<int:pk>/', ShortenedURLDetailView.as_view(), name='url-detail'),
]