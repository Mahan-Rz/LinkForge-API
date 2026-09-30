from django.http import HttpResponseRedirect
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .services import get_redirect_target, invalidate_redirect_cache
from .models import ShortenedURL
from .serializers import ShortenedURLSerializer


class ShortenedURLPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ShortenedURLListCreateView(generics.ListCreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = ShortenedURL.objects.all()
    serializer_class = ShortenedURLSerializer
    pagination_class = ShortenedURLPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['original_url']
    ordering_fields = ['created_at', 'click_count']
    ordering = ['-created_at']
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

    def perform_update(self, serializer):
        shortened_code = serializer.instance.shortened_code
        serializer.save()
        invalidate_redirect_cache(shortened_code)

    def perform_destroy(self, instance):
        invalidate_redirect_cache(instance.shortened_code)
        instance.delete()


def redirect_shortened_url(request, shortened_code):
    return HttpResponseRedirect(get_redirect_target(shortened_code))
