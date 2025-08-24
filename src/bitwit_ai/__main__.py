# src/bitwit_ai/__main__.py

import logging
import sys
import datetime # NEW: Re-added datetime import

# Import core components
from bitwit_ai.config_manager import ConfigManager
from bitwit_ai.utilities.file_utils import setup_logging
from bitwit_ai.clients.telegram_client import TelegramClient

# Import the new BitWitCoreApplication class
from bitwit_ai.application import BitWitCoreApplication

# Setup logging first (this remains here as the very first step)
config = ConfigManager() # Initialize ConfigManager first to get LOG_LEVEL
log_level_str = config.get('LOG_LEVEL', 'INFO') # Get log level string
log_level = getattr(logging, log_level_str.upper(), logging.INFO)
setup_logging(log_level=log_level)
log = logging.getLogger(__name__) # Get logger after setup_logging

# Initialize TelegramClient for initial program start messages/errors
# This is done here so that even if BitWitCoreApplication fails to initialize,
# we can still send an alert.
telegram_client_for_init_alerts = TelegramClient(config)
program_start_message = f"AI program started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
telegram_client_for_init_alerts.send_message(program_start_message)
log.info(program_start_message)


# --- Main Application Entry Point ---
if __name__ == "__main__":
    try:
        # Instantiate the core application
        # All component initialization (DB, Gemini, Bot, etc.) is now handled within BitWitCoreApplication
        app = BitWitCoreApplication(config)
        
        # Run the main application logic
        app.run()

    except Exception as e:
        error_msg = f"An unhandled critical error occurred during application execution: {e}"
        log.exception(error_msg) # Log full traceback
        # Attempt to send a Telegram alert for critical unhandled errors
        telegram_client_for_init_alerts.send_message(f"🚨 BitWit\\.AI Critical Error: {telegram_client_for_init_alerts._escape_markdown_v2(str(e))}")
        sys.exit(1)

