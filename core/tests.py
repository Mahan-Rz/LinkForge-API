from django.test import TestCase

from .serializers import ShortenedURLSerializer


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
