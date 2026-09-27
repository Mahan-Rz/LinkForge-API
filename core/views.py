from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from .models import ShortenedURL
from .serializers import ShortenedURLSerializer


class ShortenedURLListCreateView(generics.ListCreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = ShortenedURL.objects.all()
    serializer_class = ShortenedURLSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ShortenedURLDetailView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = ShortenedURL.objects.all()
    serializer_class = ShortenedURLSerializer
    http_method_names = ['get', 'put', 'delete', 'head', 'options']

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)
