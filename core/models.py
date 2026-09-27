from django.conf import settings
from django.db import models


class ShortenedURL(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shortened_urls',)
    original_url = models.URLField()
    shortened_code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    click_count = models.PositiveBigIntegerField(default=0)
    last_clicked_at = models.DateTimeField(null=True, blank=True)
