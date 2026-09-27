import secrets
import string

from rest_framework import serializers

from .models import ShortenedURL


class ShortenedURLSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortenedURL
        fields = (
            'id',
            'owner',
            'original_url',
            'shortened_code',
            'created_at',
            'click_count',
            'last_clicked_at',
        )
        read_only_fields = (
            'id',
            'owner',
            'shortened_code',
            'created_at',
            'click_count',
            'last_clicked_at',
        )

    def create(self, validated_data):
        alphabet = string.ascii_letters + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            if not ShortenedURL.objects.filter(shortened_code=code).exists():
                break

        return ShortenedURL.objects.create(
            shortened_code=code,
            **validated_data,
        )
