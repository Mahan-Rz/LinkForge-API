from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import ShortenedURL
from .serializers import ShortenedURLSerializer


class ShortenedURLAPITests(APITestCase):
    def setUp(self):
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
                'shortened_code': 'manual123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['original_url'], 'https://example.com/path')
        self.assertEqual(len(response.data['shortened_code']), 8)
        self.assertEqual(response.data['owner'], self.user.pk)
        self.assertIn('created_at', response.data)
        self.assertEqual(ShortenedURL.objects.get().owner, self.user)

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
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], own_url.id)

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


class ShortenedURLSerializerTests(TestCase):
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

    def test_rejects_an_invalid_original_url(self):
        serializer = ShortenedURLSerializer(data={'original_url': 'not a URL'})

        self.assertFalse(serializer.is_valid())
        self.assertIn('original_url', serializer.errors)
