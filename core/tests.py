from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient, APITestCase

from . import services
from .models import ClickEvent, ShortenedURL
from .serializers import MAX_CODE_GENERATION_ATTEMPTS, ShortenedURLSerializer


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'linkforge-redirect-tests',
        }
    }
)
class ShortenedURLAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.list_url = reverse('url-list-create')
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='owner',
            password='test-password',
        )
        self.other_user = user_model.objects.create_user(
            username='other',
            password='test-password',
        )
        self.client.force_authenticate(user=self.user)

    def test_create_url_for_authenticated_user(self):
        response = self.client.post(
            self.list_url,
            {
                'original_url': 'https://example.com/path',
                'owner': self.other_user.pk,
                'shortened_code': 'manual12',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['original_url'], 'https://example.com/path')
        self.assertEqual(len(response.data['shortened_code']), 8)
        self.assertNotEqual(response.data['shortened_code'], 'manual12')
        self.assertEqual(response.data['owner'], self.user.pk)
        self.assertIn('created_at', response.data)
        self.assertEqual(ShortenedURL.objects.get().owner, self.user)

    def test_create_rejects_invalid_original_url(self):
        response = self.client.post(
            self.list_url,
            {'original_url': 'not a URL'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('original_url', response.data)
        self.assertEqual(ShortenedURL.objects.count(), 0)

    def test_url_crud_requires_authentication(self):
        response = APIClient().get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_endpoint_returns_a_token_for_valid_credentials(self):
        token_client = APIClient()
        response = token_client.post(
            reverse('api-token-auth'),
            {'username': 'owner', 'password': 'test-password'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['token'])
        token_client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")

        authenticated_response = token_client.get(self.list_url)

        self.assertEqual(authenticated_response.status_code, status.HTTP_200_OK)

    def test_list_urls(self):
        own_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
            owner=self.user,
        )
        ShortenedURL.objects.create(
            original_url='https://example.org/path',
            shortened_code='def12345',
            owner=self.other_user,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], own_url.id)

    def test_list_urls_supports_pagination(self):
        for index in range(12):
            ShortenedURL.objects.create(
                original_url=f'https://example.com/path/{index}',
                shortened_code=f'page{index:04d}',
                owner=self.user,
            )

        response = self.client.get(self.list_url)
        second_page = self.client.get(self.list_url, {'page': 2})
        small_page = self.client.get(self.list_url, {'page_size': 3})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 12)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(len(second_page.data['results']), 2)
        self.assertEqual(len(small_page.data['results']), 3)

    def test_list_urls_can_search_original_url(self):
        matching_url = ShortenedURL.objects.create(
            original_url='https://example.com/search-term',
            shortened_code='search01',
            owner=self.user,
        )
        ShortenedURL.objects.create(
            original_url='https://example.org/other',
            shortened_code='search02',
            owner=self.user,
        )

        response = self.client.get(self.list_url, {'search': 'search-term'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], matching_url.id)

    def test_list_urls_can_order_by_click_count(self):
        lower_click_url = ShortenedURL.objects.create(
            original_url='https://example.com/fewer-clicks',
            shortened_code='order001',
            owner=self.user,
            click_count=1,
        )
        higher_click_url = ShortenedURL.objects.create(
            original_url='https://example.com/more-clicks',
            shortened_code='order002',
            owner=self.user,
            click_count=5,
        )

        response = self.client.get(self.list_url, {'ordering': '-click_count'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['id'] for item in response.data['results']],
            [higher_click_url.id, lower_click_url.id],
        )

    def test_list_ordering_rejects_unapproved_fields(self):
        first_url = ShortenedURL.objects.create(
            original_url='https://example.com/first',
            shortened_code='allow001',
            owner=self.user,
        )
        second_url = ShortenedURL.objects.create(
            original_url='https://example.com/second',
            shortened_code='allow002',
            owner=self.user,
        )

        response = self.client.get(self.list_url, {'ordering': 'owner'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['id'] for item in response.data['results']],
            [second_url.id, first_url.id],
        )

    def test_list_urls_can_order_by_created_at(self):
        older_url = ShortenedURL.objects.create(
            original_url='https://example.com/older',
            shortened_code='time0001',
            owner=self.user,
        )
        newer_url = ShortenedURL.objects.create(
            original_url='https://example.com/newer',
            shortened_code='time0002',
            owner=self.user,
        )
        ShortenedURL.objects.filter(pk=older_url.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        response = self.client.get(self.list_url, {'ordering': 'created_at'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['id'] for item in response.data['results']],
            [older_url.id, newer_url.id],
        )

    def test_retrieve_url(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
            owner=self.user,
        )

        response = self.client.get(reverse('url-detail', args=[shortened_url.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['original_url'], shortened_url.original_url)

    def test_cannot_retrieve_another_users_url(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
            owner=self.other_user,
        )

        response = self.client.get(reverse('url-detail', args=[shortened_url.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_url_with_put(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/old',
            shortened_code='abc12345',
            owner=self.user,
        )

        response = self.client.put(
            reverse('url-detail', args=[shortened_url.id]),
            {'original_url': 'https://example.com/new'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        shortened_url.refresh_from_db()
        self.assertEqual(shortened_url.original_url, 'https://example.com/new')
        self.assertEqual(shortened_url.shortened_code, 'abc12345')

    def test_cannot_update_another_users_url(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/old',
            shortened_code='abc12345',
            owner=self.other_user,
        )

        response = self.client.put(
            reverse('url-detail', args=[shortened_url.id]),
            {'original_url': 'https://example.com/new'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        shortened_url.refresh_from_db()
        self.assertEqual(shortened_url.original_url, 'https://example.com/old')

    def test_delete_url(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
            owner=self.user,
        )

        response = self.client.delete(reverse('url-detail', args=[shortened_url.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ShortenedURL.objects.filter(pk=shortened_url.id).exists())

    def test_cannot_delete_another_users_url(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
            owner=self.other_user,
        )

        response = self.client.delete(reverse('url-detail', args=[shortened_url.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(ShortenedURL.objects.filter(pk=shortened_url.id).exists())

    def test_patch_is_not_allowed(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
            owner=self.user,
        )

        response = self.client.patch(
            reverse('url-detail', args=[shortened_url.id]),
            {'original_url': 'https://example.com/new'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_redirect_increments_click_analytics(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/destination',
            shortened_code='redirect1',
            owner=self.user,
        )

        response = APIClient().get(reverse('url-redirect', args=['redirect1']))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response['Location'], shortened_url.original_url)
        shortened_url.refresh_from_db()
        self.assertEqual(shortened_url.click_count, 1)
        self.assertIsNotNone(shortened_url.last_clicked_at)
        self.assertEqual(
            ClickEvent.objects.filter(shortened_url=shortened_url).count(),
            1,
        )

    def test_redirect_of_active_unexpired_url_succeeds(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/active',
            shortened_code='active01',
            owner=self.user,
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = APIClient().get(reverse('url-redirect', args=['active01']))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response['Location'], shortened_url.original_url)
        self.assertEqual(ClickEvent.objects.filter(shortened_url=shortened_url).count(), 1)

    def test_inactive_url_returns_gone_without_recording_click(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/inactive',
            shortened_code='inactive',
            owner=self.user,
            is_active=False,
        )

        response = APIClient().get(reverse('url-redirect', args=['inactive']))

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        shortened_url.refresh_from_db()
        self.assertEqual(shortened_url.click_count, 0)
        self.assertIsNone(shortened_url.last_clicked_at)
        self.assertFalse(ClickEvent.objects.filter(shortened_url=shortened_url).exists())

    def test_expired_url_returns_gone_without_recording_click(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/expired',
            shortened_code='expired1',
            owner=self.user,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        response = APIClient().get(reverse('url-redirect', args=['expired1']))

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        shortened_url.refresh_from_db()
        self.assertEqual(shortened_url.click_count, 0)
        self.assertIsNone(shortened_url.last_clicked_at)
        self.assertFalse(ClickEvent.objects.filter(shortened_url=shortened_url).exists())

    def test_redirect_for_unknown_code_returns_404(self):
        response = APIClient().get(reverse('url-redirect', args=['unknown1']))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_redirect_uses_cached_target_after_first_lookup(self):
        ShortenedURL.objects.create(
            original_url='https://example.com/destination',
            shortened_code='cached01',
            owner=self.user,
        )
        with patch.object(
            services,
            '_lookup_redirect_target',
            wraps=services._lookup_redirect_target,
        ) as lookup_target:
            first_response = APIClient().get(
                reverse('url-redirect', args=['cached01'])
            )
            second_response = APIClient().get(
                reverse('url-redirect', args=['cached01'])
            )

        self.assertEqual(first_response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(second_response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(lookup_target.call_count, 1)
        self.assertEqual(
            ShortenedURL.objects.get(shortened_code='cached01').click_count,
            2,
        )
        self.assertEqual(
            ClickEvent.objects.filter(
                shortened_url__shortened_code='cached01'
            ).count(),
            2,
        )

    def test_cached_lookup_does_not_bypass_deactivation(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/deactivate',
            shortened_code='deactiv1',
            owner=self.user,
        )
        redirect_url = reverse('url-redirect', args=['deactiv1'])
        self.assertEqual(APIClient().get(redirect_url).status_code, status.HTTP_302_FOUND)
        ShortenedURL.objects.filter(pk=shortened_url.pk).update(is_active=False)

        response = APIClient().get(redirect_url)

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        shortened_url.refresh_from_db()
        self.assertEqual(shortened_url.click_count, 1)
        self.assertEqual(ClickEvent.objects.filter(shortened_url=shortened_url).count(), 1)

    def test_cached_lookup_does_not_bypass_new_expiration(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/expire',
            shortened_code='expire01',
            owner=self.user,
        )
        redirect_url = reverse('url-redirect', args=['expire01'])
        self.assertEqual(APIClient().get(redirect_url).status_code, status.HTTP_302_FOUND)
        ShortenedURL.objects.filter(pk=shortened_url.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        response = APIClient().get(redirect_url)

        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        shortened_url.refresh_from_db()
        self.assertEqual(shortened_url.click_count, 1)
        self.assertEqual(ClickEvent.objects.filter(shortened_url=shortened_url).count(), 1)

    def test_cached_id_uses_current_destination_from_database(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/old-destination',
            shortened_code='dest0001',
            owner=self.user,
        )
        redirect_url = reverse('url-redirect', args=['dest0001'])
        APIClient().get(redirect_url)
        ShortenedURL.objects.filter(pk=shortened_url.pk).update(
            original_url='https://example.com/current-destination'
        )

        response = APIClient().get(redirect_url)

        self.assertEqual(
            response['Location'],
            'https://example.com/current-destination',
        )

    def test_url_update_invalidates_cached_redirect_target(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/old',
            shortened_code='update01',
            owner=self.user,
        )
        redirect_url = reverse('url-redirect', args=['update01'])
        APIClient().get(redirect_url)

        update_response = self.client.put(
            reverse('url-detail', args=[shortened_url.id]),
            {'original_url': 'https://example.com/new'},
            format='json',
        )
        redirect_response = APIClient().get(redirect_url)

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(redirect_response['Location'], 'https://example.com/new')

    def test_url_delete_invalidates_cached_redirect_target(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/destination',
            shortened_code='delete01',
            owner=self.user,
        )
        redirect_url = reverse('url-redirect', args=['delete01'])
        APIClient().get(redirect_url)

        delete_response = self.client.delete(
            reverse('url-detail', args=[shortened_url.id])
        )
        with patch.object(
            services,
            '_lookup_redirect_target',
            wraps=services._lookup_redirect_target,
        ) as lookup_target:
            redirect_response = APIClient().get(redirect_url)

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(redirect_response.status_code, status.HTTP_404_NOT_FOUND)
        lookup_target.assert_called_once_with('delete01')

    def test_redis_failure_falls_back_to_database(self):
        ShortenedURL.objects.create(
            original_url='https://example.com/fallback',
            shortened_code='fallback',
            owner=self.user,
        )

        with self.assertLogs('core.services', level='ERROR'):
            with (
                patch('core.services.cache.get', side_effect=RedisError),
                patch('core.services.cache.set', side_effect=RedisError),
            ):
                response = APIClient().get(
                    reverse('url-redirect', args=['fallback'])
                )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response['Location'], 'https://example.com/fallback')


class ShortenedURLSerializerTests(TestCase):
    def test_accepts_future_expiration(self):
        serializer = ShortenedURLSerializer(data={
            'original_url': 'https://example.com/path',
            'expires_at': '2099-01-01T00:00:00Z',
            'is_active': False,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertFalse(serializer.validated_data['is_active'])

    def test_rejects_past_expiration(self):
        serializer = ShortenedURLSerializer(data={
            'original_url': 'https://example.com/path',
            'expires_at': '2000-01-01T00:00:00Z',
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('expires_at', serializer.errors)

    def test_create_generates_a_unique_shortened_code(self):
        user = get_user_model().objects.create_user(
            username='serializer-owner',
            password='test-password',
        )
        serializer = ShortenedURLSerializer(
            data={'original_url': 'https://example.com/path'}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        shortened_url = serializer.save(owner=user)

        self.assertEqual(len(shortened_url.shortened_code), 8)
        self.assertTrue(shortened_url.shortened_code.isalnum())
        self.assertTrue(shortened_url.created_at)
        self.assertEqual(serializer.data['shortened_code'], shortened_url.shortened_code)

        another_serializer = ShortenedURLSerializer(
            data={'original_url': 'https://example.org/another-path'}
        )
        self.assertTrue(another_serializer.is_valid(), another_serializer.errors)
        another_shortened_url = another_serializer.save(owner=user)

        self.assertNotEqual(shortened_url.shortened_code, another_shortened_url.shortened_code)

    def test_code_generator_retries_when_code_already_exists(self):
        user = get_user_model().objects.create_user(
            username='collision-owner',
            password='test-password',
        )
        ShortenedURL.objects.create(
            original_url='https://example.com/existing',
            shortened_code='collide1',
            owner=user,
        )
        serializer = ShortenedURLSerializer(
            data={'original_url': 'https://example.com/new'}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch(
            'core.serializers.generate_shortened_code',
            side_effect=['collide1', 'unique01'],
        ) as generate_code:
            shortened_url = serializer.save(owner=user)

        self.assertEqual(shortened_url.shortened_code, 'unique01')
        self.assertEqual(generate_code.call_count, 2)

    def test_code_generator_retries_a_database_unique_collision(self):
        user = get_user_model().objects.create_user(
            username='race-owner',
            password='test-password',
        )
        serializer = ShortenedURLSerializer(
            data={'original_url': 'https://example.com/new'}
        )
        actual_create = ShortenedURL.objects.create
        create_attempts = 0

        def create_with_race(**kwargs):
            nonlocal create_attempts
            create_attempts += 1
            if create_attempts == 1:
                raise IntegrityError('unique constraint')
            return actual_create(**kwargs)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with (
            patch(
                'core.serializers.generate_shortened_code',
                side_effect=['race0001', 'unique01'],
            ),
            patch('core.serializers.ShortenedURL.objects.filter') as filter_query,
            patch(
                'core.serializers.ShortenedURL.objects.create',
                side_effect=create_with_race,
            ),
        ):
            filter_query.return_value.exists.side_effect = [False, True, False]
            shortened_url = serializer.save(owner=user)

        self.assertEqual(shortened_url.shortened_code, 'unique01')
        self.assertEqual(create_attempts, 2)

    def test_code_generator_fails_cleanly_after_repeated_collisions(self):
        user = get_user_model().objects.create_user(
            username='retries-owner',
            password='test-password',
        )
        ShortenedURL.objects.create(
            original_url='https://example.com/existing',
            shortened_code='collide1',
            owner=user,
        )
        serializer = ShortenedURLSerializer(
            data={'original_url': 'https://example.com/new'}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch(
            'core.serializers.generate_shortened_code',
            return_value='collide1',
        ) as generate_code:
            with self.assertRaises(ValidationError):
                serializer.save(owner=user)

        self.assertEqual(generate_code.call_count, MAX_CODE_GENERATION_ATTEMPTS)
        self.assertEqual(ShortenedURL.objects.count(), 1)

    def test_rejects_an_invalid_original_url(self):
        serializer = ShortenedURLSerializer(data={'original_url': 'not a URL'})

        self.assertFalse(serializer.is_valid())
        self.assertIn('original_url', serializer.errors)
