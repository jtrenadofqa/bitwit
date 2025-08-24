# tests/integration/test_telegram_client.py

import unittest
import os
import sys
import logging
import tempfile
from pathlib import Path
import datetime
from unittest.mock import MagicMock
import random

# Add the project's root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import actual components from your bitwit_ai package
from bitwit_ai.config_manager import ConfigManager
from bitwit_ai.clients.telegram_client import TelegramClient

# Suppress excessive logging from libraries during tests for cleaner output
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
# Set a higher level for the test's own logger to see test progress
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG) # Set to DEBUG to see more detailed logs for this test
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)


class TestTelegramClientIntegration(unittest.TestCase):
    """
    Integration tests for TelegramClient.
    These tests make actual API calls to Telegram.
    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to be set in .env.
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
        cls.bot_token = cls.config.get('TELEGRAM_BOT_TOKEN')
        cls.chat_id = cls.config.get('TELEGRAM_CHAT_ID')
        cls.enable_alerts = cls.config.get('ENABLE_TELEGRAM_ALERTS', False)
        
        # Get the generated images directory from ConfigManager
        raw_picture_directory_from_config = cls.config.get('GENERATED_IMAGES_DIR')

        # Determine the project root dynamically (assuming test file is in tests/integration)
        project_root = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

        # Resolve the picture directory relative to the project root
        if raw_picture_directory_from_config:
            cls.picture_directory = project_root / Path(raw_picture_directory_from_config)
        else:
            raise unittest.SkipTest("GENERATED_IMAGES_DIR not configured in .env. Cannot run photo tests.")

        if not cls.bot_token or not cls.chat_id or not cls.enable_alerts:
            raise unittest.SkipTest(
                "Telegram BOT_TOKEN, CHAT_ID, or ENABLE_TELEGRAM_ALERTS not configured "
                "or enabled in .env. Skipping TelegramClient integration tests. "
                "Please set these variables for these tests to run."
            )
        
        cls.telegram_client = TelegramClient(cls.config)
        log.info("TelegramClient initialized for integration tests.")

        # Select a random existing image from the specified directory
        if not cls.picture_directory.exists():
            raise unittest.SkipTest(f"Picture directory not found at: {cls.picture_directory}. Cannot run photo tests.")

        image_files = [f for f in os.listdir(cls.picture_directory) if Path(cls.picture_directory / f).is_file() and Path(f).suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif')]
        
        if not image_files:
            raise unittest.SkipTest(f"No image files found in {cls.picture_directory}. Skipping photo tests.")

        cls.selected_image_path = cls.picture_directory / random.choice(image_files)
        log.info(f"Selected random image for testing: {cls.selected_image_path}")

    @classmethod
    def tearDownClass(cls):
        """
        Clean up resources after all tests in this class have run.
        No temporary files are created by this test, so no specific cleanup is needed.
        """
        log.info("No temporary image files to clean up as existing images are used.")

    def test_send_message_success(self):
        """
        Tests sending a simple text message successfully.
        """
        log.info("Running test_send_message_success")
        message = f"Hello from BitWit.AI test! This is a test message at {datetime.datetime.now().strftime('%H:%M:%S')}."
        success = self.telegram_client.send_message(message)
        self.assertTrue(success, "Failed to send a simple Telegram message.")
        log.info("Successfully sent a test message to Telegram.")

    def test_send_message_with_markdown_v2(self):
        """
        Tests sending a message with MarkdownV2 formatting.
        """
        log.info("Running test_send_message_with_markdown_v2")
        message = (
            f"This is a *bold* message from _BitWit\\.AI_ test at `{datetime.datetime.now().strftime('%H:%M:%S')}`.\n"
            "It includes `code` and a [link to Google](https://www.google.com)."
        )
        success = self.telegram_client.send_message(message, parse_mode="MarkdownV2")
        self.assertTrue(success, "Failed to send a MarkdownV2 formatted message.")
        log.info("Successfully sent a MarkdownV2 message to Telegram.")

    def test_send_photo_success(self):
        """
        Tests sending a photo with a caption successfully.
        """
        log.info("Running test_send_photo_success")
        caption = f"Test photo from BitWit\\.AI at `{datetime.datetime.now().strftime('%H:%M:%S')}`. This is a _caption_."
        
        log.debug(f"Attempting to send photo from path: {self.selected_image_path}")
        if not self.selected_image_path.exists():
            log.error(f"ERROR: Selected image file DOES NOT EXIST at {self.selected_image_path} before send_photo call. This is unexpected.")
            self.fail(f"Selected image file {self.selected_image_path} does not exist. Check setUpClass and GENERATED_IMAGES_DIR config.")
        else:
            log.debug(f"DEBUG: Selected image file EXISTS at {self.selected_image_path} before send_photo call.")

        # FIX: Pass the string path directly to send_photo, as it expects a path
        success = self.telegram_client.send_photo(str(self.selected_image_path), caption=caption, parse_mode="MarkdownV2")
        self.assertTrue(success, "Failed to send a photo to Telegram.")
        log.info("Successfully sent a test photo to Telegram.")

    def test_send_photo_no_file(self):
        """
        Tests sending a photo with a non-existent file path.
        Should return False and log a warning.
        """
        log.info("Running test_send_photo_no_file")
        # FIX: Pass a non-existent path string, as send_photo expects a path
        non_existent_path = "/path/to/non_existent_image.png"
        success = self.telegram_client.send_photo(non_existent_path, caption="Should fail with non-existent path.")
        self.assertFalse(success, "Sending photo with non-existent file should fail.")
        log.info("Correctly failed to send photo with non-existent file.")

    def test_send_message_disabled_alerts(self):
        """
        Tests that messages are not sent when alerts are disabled.
        This requires re-initializing the client with alerts disabled.
        """
        log.info("Running test_send_message_disabled_alerts")
        disabled_config = MagicMock()
        disabled_config.get.side_effect = lambda key, default=None: {
            'TELEGRAM_BOT_TOKEN': self.bot_token,
            'TELEGRAM_CHAT_ID': self.chat_id,
            'ENABLE_TELEGRAM_ALERTS': False
        }.get(key, default)
        
        disabled_client = TelegramClient(disabled_config)
        
        message = "This message should NOT be sent."
        success = disabled_client.send_message(message)
        self.assertFalse(success, "Message should not be sent when alerts are disabled.")
        log.info("Correctly skipped sending message when alerts disabled.")


if __name__ == '__main__':
    unittest.main()
