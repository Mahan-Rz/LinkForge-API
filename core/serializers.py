import secrets
import string

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from .models import ShortenedURL

CODE_LENGTH = 8
MAX_CODE_GENERATION_ATTEMPTS = 5


def generate_shortened_code():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(CODE_LENGTH))


class ShortenedURLSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortenedURL
        fields = (
            'id',
            'owner',
            'original_url',
            'shortened_code',
            'created_at',
            'expires_at',
            'is_active',
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

    def validate_expires_at(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError(
                'Expiration must be a future date and time.'
            )
        return value

    def create(self, validated_data):
        for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
            code = generate_shortened_code()
            if ShortenedURL.objects.filter(shortened_code=code).exists():
                continue

            try:
                with transaction.atomic():
                    return ShortenedURL.objects.create(
                        shortened_code=code,
                        **validated_data,
                    )
            except IntegrityError:
                if ShortenedURL.objects.filter(shortened_code=code).exists():
                    continue
                raise

        raise serializers.ValidationError({
            'shortened_code': 'Could not generate a unique code. Please try again.'
        })
