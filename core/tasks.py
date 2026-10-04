import logging

from celery import shared_task
from django.db import OperationalError, transaction
from django.db.models import Q
from django.utils import timezone

from .models import ShortenedURL
from .services import invalidate_redirect_cache

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def deactivate_expired_urls():
    now = timezone.now()

    with transaction.atomic():
        expired_urls = list(
            ShortenedURL.objects.select_for_update()
            .filter(
                is_active=True,
                expires_at__isnull=False,
                expires_at__lte=now,
            )
            .values_list('id', 'shortened_code')
        )
        if not expired_urls:
            return 0

        expired_ids = [url_id for url_id, _ in expired_urls]
        updated_count = ShortenedURL.objects.filter(
            pk__in=expired_ids,
            is_active=True,
        ).filter(
            Q(expires_at__isnull=False, expires_at__lte=now)
        ).update(is_active=False)

    if updated_count:
        for _, shortened_code in expired_urls:
            invalidate_redirect_cache(shortened_code)

    logger.info('Deactivated %d expired shortened URLs.', updated_count)
    return updated_count
