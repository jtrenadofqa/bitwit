# src/bitwit_ai/clients/telegram_client.py

import os
import requests
import logging
import re
from typing import Optional
from bitwit_ai.config_manager import ConfigManager # Import ConfigManager to get settings

log = logging.getLogger(__name__)

class TelegramClient:
    """
    Client for sending messages and photos to a Telegram bot.
    Handles API interactions and MarkdownV2 escaping.
    """
    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the TelegramClient.
        :param config_manager: An instance of ConfigManager to retrieve Telegram settings.
        """
        self.config = config_manager
        self.bot_token = self.config.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = self.config.get('TELEGRAM_CHAT_ID')
        self.enable_alerts = self.config.get('ENABLE_TELEGRAM_ALERTS', False) # Default to False

        if not self.bot_token or not self.chat_id:
            log.warning("Telegram BOT_TOKEN or CHAT_ID not configured. Telegram alerts will be disabled.")
            self.enable_alerts = False
        elif self.enable_alerts:
            log.info("TelegramClient initialized and enabled.")
        else:
            log.info("TelegramClient initialized but alerts are disabled by configuration.")

    def _escape_markdown_v2(self, text: str) -> str:
        """
        Escapes special characters in text to be compatible with Telegram's MarkdownV2 parse mode.
        See: https://core.telegram.org/bots/api#markdownv2-style
        """
        escaped_text = text.replace('\\', '\\\\')
        special_chars_pattern = r'([_*\[\]()~`>#+\-=\|\{\}.!])'
        escaped_text = re.sub(special_chars_pattern, r'\\\1', escaped_text)
        return escaped_text

    def send_message(self, message: str, parse_mode: str = "MarkdownV2") -> bool:
        """
        Sends a text message to the configured Telegram chat.
        Automatically escapes message content for MarkdownV2 if that parse_mode is used.
        :param message: The text message to send.
        :param parse_mode: The parse mode for the message (e.g., "MarkdownV2", "HTML", "None").
        :return: True if the message was sent successfully, False otherwise.
        """
        if not self.enable_alerts:
            log.debug("Telegram alerts are disabled. Skipping message send.")
            return False

        if not self.bot_token or not self.chat_id:
            log.error("Telegram BOT_TOKEN or CHAT_ID is missing. Cannot send message.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        processed_message = message
        if parse_mode == "MarkdownV2":
            processed_message = self._escape_markdown_v2(message)

        payload = {
            "chat_id": self.chat_id,
            "text": processed_message,
            "parse_mode": parse_mode
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            log.info(f"Telegram message sent successfully: {message[:50]}...")
            return True
        except requests.exceptions.RequestException as e:
            log.error(f"Error sending Telegram message: {e}")
            if e.response:
                log.error(f"Telegram API response: {e.response.text}")
            return False
        except Exception as e:
            log.error(f"An unexpected error occurred while sending Telegram message: {e}")
            return False

    def send_photo(self, photo_path: str, caption: Optional[str] = None, parse_mode: str = "MarkdownV2") -> bool:
        """
        Sends a photo to the configured Telegram chat from a local file path.
        :param photo_path: The local file path to the photo to send.
        :param caption: An optional caption for the photo.
        :param parse_mode: The parse mode for the caption (e.g., "MarkdownV2", "HTML", "None").
        :return: True if the photo was sent successfully, False otherwise.
        """
        if not self.enable_alerts:
            log.debug("Telegram alerts are disabled. Skipping photo send.")
            return False

        if not self.bot_token or not self.chat_id:
            log.error("Telegram BOT_TOKEN or CHAT_ID is missing. Cannot send photo.")
            return False

        if not photo_path or not os.path.exists(photo_path):
            log.warning(f"Photo file not found or path is empty: {photo_path}. Skipping Telegram photo send.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        
        processed_caption = caption
        if caption and parse_mode == "MarkdownV2":
            processed_caption = self._escape_markdown_v2(caption)

        try:
            with open(photo_path, 'rb') as f: # Read the image bytes from the file
                files = {'photo': (os.path.basename(photo_path), f.read(), 'image/png')}
            
            data = {'chat_id': self.chat_id}
            if processed_caption:
                data['caption'] = processed_caption
                data['parse_mode'] = parse_mode

            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            log.info(f"Telegram photo from {photo_path} sent successfully.")
            return True
        except FileNotFoundError:
            log.error(f"Error: Photo file not found at {photo_path}.")
            return False
        except IOError as io_err:
            log.error(f"Error reading photo file {photo_path}: {io_err}.")
            return False
        except requests.exceptions.RequestException as e:
            log.error(f"Error sending Telegram photo: {e}")
            if e.response:
                log.error(f"Telegram API response: {e.response.text}")
            return False
        except Exception as e:
            log.error(f"An unexpected error occurred while sending Telegram photo from {photo_path}: {e}")
            return False

