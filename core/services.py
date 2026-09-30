import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Q
from django.http import Http404
from django.utils import timezone
from redis.exceptions import RedisError

from .models import ClickEvent, ShortenedURL

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 300


def _cache_key(shortened_code):
    return f'linkforge:redirect:{shortened_code}'


def _lookup_redirect_target(shortened_code):
    try:
        return ShortenedURL.objects.values('id').get(
            shortened_code=shortened_code
        )
    except ShortenedURL.DoesNotExist as exc:
        raise Http404('Shortened URL not found.') from exc


def invalidate_redirect_cache(shortened_code):
    try:
        cache.delete(_cache_key(shortened_code))
    except RedisError:
        logger.exception(
            'Redis cache invalidation failed for shortened code %s.',
            shortened_code,
        )


def get_redirect_target(shortened_code):
    key = _cache_key(shortened_code)
    try:
        cached_target = cache.get(key)
    except RedisError:
        logger.exception(
            'Redis cache lookup failed for shortened code %s.',
            shortened_code,
        )
        cached_target = None

    if (
        isinstance(cached_target, int)
    ):
        url_id = cached_target
    else:
        target = _lookup_redirect_target(shortened_code)
        url_id = target['id']
        try:
            cache.set(key, url_id, timeout=CACHE_TIMEOUT)
        except RedisError:
            logger.exception(
                'Redis cache population failed for shortened code %s.',
                shortened_code,
            )

    with transaction.atomic():
        try:
            shortened_url = ShortenedURL.objects.select_for_update().get(
                pk=url_id,
                shortened_code=shortened_code,
            )
        except ShortenedURL.DoesNotExist as exc:
            invalidate_redirect_cache(shortened_code)
            raise Http404('Shortened URL not found.') from exc

        now = timezone.now()
        if not shortened_url.is_active or (
            shortened_url.expires_at is not None
            and shortened_url.expires_at <= now
        ):
            invalidate_redirect_cache(shortened_code)
            return None

        updated = ShortenedURL.objects.filter(
            pk=shortened_url.pk,
            is_active=True,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).update(
            click_count=F('click_count') + 1,
            last_clicked_at=now,
        )
        if not updated:
            invalidate_redirect_cache(shortened_code)
            return None

        ClickEvent.objects.create(shortened_url=shortened_url)

    return shortened_url.original_url
