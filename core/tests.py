from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ShortenedURL
from .serializers import ShortenedURLSerializer


class ShortenedURLAPITests(APITestCase):
    def setUp(self):
        self.list_url = reverse('url-list-create')

    def test_create_url_without_authentication(self):
        response = self.client.post(
            self.list_url,
            {'original_url': 'https://example.com/path'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['original_url'], 'https://example.com/path')
        self.assertEqual(len(response.data['shortened_code']), 8)
        self.assertIn('created_at', response.data)
        self.assertEqual(ShortenedURL.objects.count(), 1)

    def test_list_urls(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], shortened_url.id)

    def test_retrieve_url(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
        )

        response = self.client.get(reverse('url-detail', args=[shortened_url.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['original_url'], shortened_url.original_url)

    def test_update_url_with_put(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/old',
            shortened_code='abc12345',
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

    def test_delete_url(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
        )

        response = self.client.delete(reverse('url-detail', args=[shortened_url.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ShortenedURL.objects.filter(pk=shortened_url.id).exists())

    def test_patch_is_not_allowed(self):
        shortened_url = ShortenedURL.objects.create(
            original_url='https://example.com/path',
            shortened_code='abc12345',
        )

        response = self.client.patch(
            reverse('url-detail', args=[shortened_url.id]),
            {'original_url': 'https://example.com/new'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ShortenedURLSerializerTests(TestCase):
    def test_create_generates_a_unique_shortened_code(self):
        serializer = ShortenedURLSerializer(
            data={'original_url': 'https://example.com/path'}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        shortened_url = serializer.save()

        self.assertEqual(len(shortened_url.shortened_code), 8)
        self.assertTrue(shortened_url.shortened_code.isalnum())
        self.assertTrue(shortened_url.created_at)
        self.assertEqual(serializer.data['shortened_code'], shortened_url.shortened_code)

        another_serializer = ShortenedURLSerializer(
            data={'original_url': 'https://example.org/another-path'}
        )
        self.assertTrue(another_serializer.is_valid(), another_serializer.errors)
        another_shortened_url = another_serializer.save()

        self.assertNotEqual(shortened_url.shortened_code, another_shortened_url.shortened_code)

    def test_rejects_an_invalid_original_url(self):
        serializer = ShortenedURLSerializer(data={'original_url': 'not a URL'})

        self.assertFalse(serializer.is_valid())
        self.assertIn('original_url', serializer.errors)
