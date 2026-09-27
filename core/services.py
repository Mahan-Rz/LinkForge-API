import logging

from django.core.cache import cache
from django.db.models import F
from django.http import Http404
from django.utils import timezone
from redis.exceptions import RedisError

from .models import ShortenedURL

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 300


def _cache_key(shortened_code):
    return f'linkforge:redirect:{shortened_code}'


def _lookup_redirect_target(shortened_code):
    try:
        return ShortenedURL.objects.values('id', 'original_url').get(
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
        isinstance(cached_target, tuple)
        and len(cached_target) == 2
        and isinstance(cached_target[0], int)
        and isinstance(cached_target[1], str)
    ):
        url_id, original_url = cached_target
    else:
        target = _lookup_redirect_target(shortened_code)
        url_id = target['id']
        original_url = target['original_url']
        try:
            cache.set(key, (url_id, original_url), timeout=CACHE_TIMEOUT)
        except RedisError:
            logger.exception(
                'Redis cache population failed for shortened code %s.',
                shortened_code,
            )

    updated = ShortenedURL.objects.filter(pk=url_id).update(
        click_count=F('click_count') + 1,
        last_clicked_at=timezone.now(),
    )
    if not updated:
        invalidate_redirect_cache(shortened_code)
        raise Http404('Shortened URL not found.')

    return original_url
