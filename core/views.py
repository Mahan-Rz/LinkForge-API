from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import ShortenedURL
from .serializers import ShortenedURLSerializer


class ShortenedURLListCreateView(generics.ListCreateAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    queryset = ShortenedURL.objects.all()
    serializer_class = ShortenedURLSerializer
    http_method_names = ['get', 'post', 'head', 'options']


class ShortenedURLDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    queryset = ShortenedURL.objects.all()
    serializer_class = ShortenedURLSerializer
    http_method_names = ['get', 'put', 'delete', 'head', 'options']
