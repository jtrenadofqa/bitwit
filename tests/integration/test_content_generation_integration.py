# tests/integration/test_content_generation_integration.py

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import logging
import datetime
import tempfile # NEW: Import tempfile for temporary directories

# Add the project's root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import actual components from your bitwit_ai package
from bitwit_ai.config_manager import ConfigManager
from bitwit_ai.clients.gemini_client import GeminiClient
from bitwit_ai.bots.bot_agent import BotAgent
from bitwit_ai.bots.content_pipeline import ContentPipeline
from bitwit_ai.bots.message_formatter import MessageFormatter
from bitwit_ai.utilities.file_utils import read_markdown_persona_file # Used to load bot persona

# Suppress excessive logging from libraries during tests for cleaner output
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('google.generativeai').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('bitwit_ai.clients.gemini_client').setLevel(logging.INFO) # Keep some client logs for debugging

class TestContentGenerationIntegration(unittest.TestCase):
    """
    Integration tests for the content generation pipeline.
    These tests make actual API calls to Gemini and Imagen.
    They save generated images to a temporary directory and clean up.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up resources that are shared across all tests in this class.
        This runs once before any test methods in this class.
        """
        from dotenv import load_dotenv
        load_dotenv()

        cls.config = ConfigManager()

        if not cls.config.get('GEMINI_API_KEY') or cls.config.get('GEMINI_API_KEY') == "dummy_key_if_missing":
            raise unittest.SkipTest(
                "GEMINI_API_KEY not configured. Skipping integration tests. "
                "Please set GEMINI_API_KEY in your .env file for these tests."
            )

        persona_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../library/personalities/bitwit_v1.md'))
        if not os.path.exists(persona_file_path):
            raise FileNotFoundError(f"Bot persona file not found at: {persona_file_path}. Cannot run integration tests.")
        
        personality_content = read_markdown_persona_file(persona_file_path)
        if not personality_content:
            raise ValueError(f"Bot persona file is empty or unreadable: {persona_file_path}. Cannot run integration tests.")
        
        cls.bitwit_bot_agent = BotAgent.from_personality_markdown(personality_content)
        cls.bitwit_bot_agent.db_id = 999

    # Removed patch decorators for os.makedirs, open, os.path.exists, and datetime
    # as we will allow real file system interaction in a temporary directory.
    # os.path.join is still patched to ensure consistent path handling in test context.
    @patch('bitwit_ai.bots.content_pipeline.os.path.join', side_effect=os.path.join)
    def setUp(self, mock_content_pipeline_os_path_join):
        """
        Set up resources before each test method.
        """
        self.mock_content_pipeline_os_path_join = mock_content_pipeline_os_path_join

        # Create a temporary directory for image saving
        self.temp_dir = tempfile.TemporaryDirectory()
        self.image_output_dir_mock = self.temp_dir.name # Store the path to the temp directory

        self.mock_db_manager = MagicMock()
        self.mock_db_manager.get_recent_conversation_segments.return_value = []

        self.gemini_client = GeminiClient()
        self.message_formatter = MessageFormatter(platform_configs={'twitter_char_limit': 280})
        
        self.patcher_config_get = patch.object(self.config, 'get')
        self.mock_config_get = self.patcher_config_get.start()

        def default_config_get_side_effect(key):
            if key == 'GENERATED_IMAGES_DIR':
                return self.image_output_dir_mock # Return the temporary directory path
            return self.config._config.get(key)

        self.mock_config_get.side_effect = default_config_get_side_effect

        self.content_pipeline = ContentPipeline(
            gemini_client=self.gemini_client,
            db_manager=self.mock_db_manager,
            message_formatter=self.message_formatter,
            config_manager=self.config
        )


    def tearDown(self):
        """
        Clean up resources after each test method.
        """
        self.patcher_config_get.stop()
        self.temp_dir.cleanup() # Clean up the temporary directory
        pass

    def _set_image_generation_config(self, enable: bool, chance: float):
        """Helper to set image generation config for specific tests."""
        def custom_get_side_effect(key):
            if key == 'ENABLE_IMAGE_GENERATION':
                return enable
            elif key == 'IMAGE_GENERATION_CHANCE':
                return chance
            elif key == 'GENERATED_IMAGES_DIR':
                return self.image_output_dir_mock # Ensure this also returns the temporary directory
            return self.config._config.get(key)

        self.mock_config_get.side_effect = custom_get_side_effect


    def test_generate_content_with_image(self):
        """
        Tests content generation including image generation.
        This will make real API calls to Gemini and Imagen.
        The generated image will be saved to a temporary directory.
        """
        self._set_image_generation_config(enable=True, chance=1.0) # Force image generation

        print("\n--- Running Integration Test: Content with Image ---")
        
        generated_content = self.content_pipeline.generate_content(self.bitwit_bot_agent)

        self.assertIsNotNone(generated_content)
        self.assertIn('text_content', generated_content)
        self.assertIn('image_path', generated_content)

        self.assertIsInstance(generated_content['text_content'], str)
        self.assertTrue(len(generated_content['text_content']) > 50)

        self.assertIsInstance(generated_content['image_path'], str)
        self.assertIsNotNone(generated_content['image_path'])
        
        # Verify the image path is within the temporary directory and the file exists
        self.assertTrue(generated_content['image_path'].startswith(self.image_output_dir_mock))
        self.assertTrue(os.path.exists(generated_content['image_path']))
        self.assertTrue(os.path.getsize(generated_content['image_path']) > 0) # Ensure file is not empty


        print(f"Generated Tweet (Integration Test):\n{generated_content['text_content']}")
        print(f"Generated Image Path (Integration Test): {generated_content['image_path']}")


    def test_generate_content_no_image(self):
        """
        Tests content generation without image generation (due to chance).
        This will make a real API call to Gemini for text, but not Imagen.
        """
        self._set_image_generation_config(enable=True, chance=0.0) # Prevent image generation via chance

        print("\n--- Running Integration Test: Content without Image ---")
        generated_content = self.content_pipeline.generate_content(self.bitwit_bot_agent)

        self.assertIsNotNone(generated_content)
        self.assertIn('text_content', generated_content)
        self.assertIn('image_path', generated_content)

        self.assertIsInstance(generated_content['text_content'], str)
        self.assertTrue(len(generated_content['text_content']) > 50)

        self.assertIsNone(generated_content['image_path']) # No image path expected

        # Assert no image file was created in the temporary directory
        self.assertEqual(len(os.listdir(self.image_output_dir_mock)), 0)


        print(f"Generated Tweet (Integration Test):\n{generated_content['text_content']}")
        print("Image (Integration Test): Not generated as expected.")


if __name__ == '__main__':
    unittest.main()
