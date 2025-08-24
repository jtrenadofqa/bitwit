# src/bitwit_ai/clients/__init__.py

# Import the clients you want to expose from this package
from .gemini_client import GeminiClient
from .telegram_client import TelegramClient # NEW: Import TelegramClient

# Define what gets imported when someone does 'from bitwit_ai.clients import *'
__all__ = [
    'GeminiClient',
    'TelegramClient' # NEW: Add TelegramClient to __all__
]