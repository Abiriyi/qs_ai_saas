from django.test import SimpleTestCase
from django.conf import settings


class OpenAISettingsConfigurationTest(SimpleTestCase):
    def test_openai_settings_are_exposed_to_django(self):
        self.assertTrue(hasattr(settings, "OPENAI_API_KEY"))
        self.assertTrue(settings.OPENAI_API_KEY)
        self.assertEqual(settings.OPENAI_MODEL, "gpt-4.1")
