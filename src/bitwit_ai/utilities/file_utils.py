# src/bitwit_ai/utilities/file_utils.py

import os
import logging
import re
import datetime
from typing import Optional, Dict, Any, List
import uuid
import colorlog
import tarfile
import shutil
import json
import urllib.parse
from logging.handlers import TimedRotatingFileHandler

# Import ConfigManager
from bitwit_ai.config_manager import ConfigManager
# Using Any for db_manager type hint to avoid circular imports if DBManager imports file_utils
# from bitwit_ai.data_storage.db_manager import DBManager
# from bitwit_ai.data_storage.models import Post # Not directly used in this file's logic, only for type hinting in export_conversations_to_json

log = logging.getLogger(__name__)

LOG_COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

LOG_FORMAT = (
    '%(log_color)s%(levelname)-8s%(reset)s | '
    '%(white)s%(asctime)s%(reset)s | '
    '%(blue)s%(name)s:%(lineno)d%(reset)s | '
    '%(log_color)s%(message)s%(reset)s'
)

def setup_logging(log_level=logging.INFO):
    config = ConfigManager()
    log_dir = config.get('LOG_DIR')
    log_archive_dir = config.get('LOG_ARCHIVE_DIR')

    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(log_archive_dir, exist_ok=True)

    app_logger = logging.getLogger('bitwit_ai')
    app_logger.setLevel(log_level)
    for handler in app_logger.handlers[:]:
        app_logger.removeHandler(handler)

    root_logger = logging.getLogger()
    #root_logger.setLevel(log_level)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter = colorlog.ColoredFormatter(
        LOG_FORMAT,
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors=LOG_COLORS,
        secondary_log_colors={},
        style='%'
    )
    console_handler.setFormatter(formatter)
    app_logger.addHandler(console_handler)

    log_file_path = os.path.join(log_dir, 'bitwit_ai.log')
    file_handler = TimedRotatingFileHandler(
        log_file_path,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter('%(levelname)-8s | %(asctime)s | %(name)s:%(lineno)d | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    app_logger.addHandler(file_handler)
    
    app_logger.propagate = False

    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('google.generativeai').setLevel(logging.INFO)

    log.info("Logging setup complete with daily file rotation.")

    archive_old_logs(log_dir, log_archive_dir)


def archive_old_logs(log_dir: str, archive_dir: str):
    now = datetime.datetime.now()
    
    if now.day == 1:
        log.info("It's the first day of the month. Checking for logs to archive...")
        
        first_day_of_current_month = now.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - datetime.timedelta(days=1)
        
        month_to_archive = last_day_of_previous_month.strftime('%Y-%m')
        archive_filename = os.path.join(archive_dir, f"bitwit_logs_{month_to_archive}.tar.gz")

        if os.path.exists(archive_filename):
            log.info(f"Archive for {month_to_archive} already exists: {archive_filename}. Skipping archiving.")
            return

        files_to_archive = []
        for filename in os.listdir(log_dir):
            if filename.startswith('bitwit_ai.log.'):
                try:
                    file_date_str = filename.split('.log.')[1]
                    file_date = datetime.datetime.strptime(file_date_str, '%Y-%m-%d')
                    if file_date.strftime('%Y-%m') == month_to_archive:
                        files_to_archive.append(os.path.join(log_dir, filename))
                except (IndexError, ValueError):
                    log.warning(f"Could not parse date from log file: {filename}. Skipping.")
                    continue
        
        current_log_file = os.path.join(log_dir, 'bitwit_ai.log')
        if os.path.exists(current_log_file):
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(current_log_file))
            if mod_time.strftime('%Y-%m') == month_to_archive:
                files_to_archive.append(current_log_file)


        if not files_to_archive:
            log.info(f"No log files found for {month_to_archive} to archive.")
            return

        log.info(f"Archiving {len(files_to_archive)} log files for {month_to_archive} to {archive_filename}...")
        try:
            with tarfile.open(archive_filename, "w:gz") as tar:
                for file_path in files_to_archive:
                    tar.add(file_path, arcname=os.path.basename(file_path))
                    log.debug(f"Added {os.path.basename(file_path)} to archive.")
            log.info(f"Successfully archived logs to {archive_filename}.")

            for file_path in files_to_archive:
                try:
                    os.remove(file_path)
                    log.debug(f"Removed archived log file: {file_path}")
                except OSError as e:
                    log.error(f"Error removing archived log file {file_path}: {e}")

        except Exception as e:
            log.error(f"Error creating log archive {archive_filename}: {e}")
    else:
        log.debug("Not the first day of the month. Skipping log archiving check.")


def read_markdown_persona_file(filepath: str) -> Optional[str]:
    """
    Reads the raw content of a Markdown file.
    Returns the content as a string, or None if the file cannot be read.
    """
    log.debug(f"Attempting to read file: {os.path.abspath(filepath)}")
    if not os.path.exists(filepath):
        log.error(f"Personality file NOT FOUND at: {os.path.abspath(filepath)}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if not content.strip():
            log.warning(f"Personality file is empty: {os.path.abspath(filepath)}")
            return None
        log.debug("Successfully read file. Content length: %d", len(content))
        return content
    except Exception as e:
        log.error(f"Error reading personality file '{os.path.abspath(filepath)}': {e}")
        return None

def save_image_locally(image_bytes: bytes) -> str | None:
    """
    Saves image bytes to a local file within the configured directory.
    :param image_bytes: The raw bytes of the image to save.
    :return: The path to the saved image file, or None if saving fails.
    """
    if not image_bytes:
        log.warning("No image bytes provided to save locally.")
        return None

    config = ConfigManager()
    image_save_dir = config.get('GENERATED_IMAGES_DIR')

    if not image_save_dir:
        log.error("GENERATED_IMAGES_DIR is not configured. Cannot save image.")
        return None

    os.makedirs(image_save_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    image_filename = os.path.join(image_save_dir, f"bitwit_image_{timestamp}_{unique_id}.png")
    
    try:
        with open(image_filename, "wb") as f:
            f.write(image_bytes)
        log.info(f"Image saved locally to: {image_filename}")
        return image_filename
    except IOError as io_err:
        log.error(f"Error saving image locally to {image_filename}: {io_err}")
        return None
    except Exception as e:
        log.error(f"An unexpected error occurred while saving image: {e}")
        return None


def export_conversations_to_json(db_manager: Any, output_json_path: str, web_images_dir: str) -> bool:
    """
    Exports all posts from the database to a JSON file and copies associated images.
    This function is intended to prepare data for a web frontend.

    :param db_manager: An initialized DBManager instance.
    :param output_json_path: The full path to the output JSON file (e.g., 'bitwit_website/public/conversation_feed.json').
    :param web_images_dir: The directory where images should be copied for web access (e.g., 'bitwit_website/public/generated_images').
    :return: True if export was successful, False otherwise.
    """
    log.info(f"Starting conversation export to JSON: {output_json_path}")
    
    log.debug(f"DEBUG (file_utils): export_conversations_to_json called.")
    log.debug(f"DEBUG (file_utils): db_manager object ID: {id(db_manager)}")
    log.debug(f"DEBUG (file_utils): db_manager object type: {type(db_manager)}")
    if hasattr(db_manager, 'enable_read'):
        log.debug(f"DEBUG (file_utils): db_manager.enable_read value: {db_manager.enable_read}")

    if not db_manager or not getattr(db_manager, 'enable_read', False):
        log.error("DBManager is not provided or read access is not enabled. Cannot export conversations.")
        return False

    try:
        all_posts = db_manager.get_all_posts_with_bot_names()
        export_data = []

        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        # We no longer copy images here, so web_images_dir doesn't need to be created/managed for copies.
        # os.makedirs(web_images_dir, exist_ok=True) # This line is no longer needed for image copying

        config = ConfigManager()
        generated_images_base_dir = config.get('GENERATED_IMAGES_DIR')
        web_image_dir_path = config.get('WEBSITE_IMAGES_WEB_PATH')

        for post in all_posts:
            web_image_path = None
            if post.image_url:
                original_image_full_path = post.image_url # This is the path in GENERATED_IMAGES_DIR
                
                image_filename = os.path.basename(original_image_full_path)
                original_image_full_path = f"{generated_images_base_dir}/{image_filename}"
                
                
                # Construct the web-accessible path.
                # This relies on the `npm run build` script creating a symlink from build/generated_images
                # to the actual GENERATED_IMAGES_DIR.
                web_image_path = f"/generated_images/{image_filename}"
                
                # IMPORTANT: We are NOT copying the image here.
                # We rely on the `npm run build` script to create a symlink
                # from `bitwit_website/build/generated_images` to `GENERATED_IMAGES_DIR`.
                
                # Optional: Add a check if the physical image file exists, for robustness
                if not os.path.exists(original_image_full_path):
                    log.warning(f"Physical image file not found at {original_image_full_path} for post {post.id}. Image link might be broken on website.")
                    web_image_path = None # Set to None if image doesn't exist physically

            export_data.append({
                "id": post.id,
                "author_name": post.bot.name if post.bot else "Unknown",
                "text": post.tweet_text,
                "image_path": web_image_path,
                "timestamp": post.created_at.isoformat(),
                "in_reply_to_tweet_id": post.in_reply_to_tweet_id, # Include reply ID
                "in_reply_to_author_name": post.in_reply_to_author_name, # Include reply author
            })

        export_data.sort(key=lambda x: x['timestamp'])

        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        log.info(f"Successfully exported {len(export_data)} conversations to {output_json_path}.")

        return True

    except Exception as e:
        log.error(f"Failed to export conversations to JSON: {e}")
        return False


def reset_application():
    """
    Performs a full reset of the application's data:
    - Deletes the database.
    - Deletes the conversation_feed.json file.
    - Empties the generated images directory.
    - Empties the log directories (daily logs and archives).
    """
    log.info("--- Starting BitWit.AI Application Reset (via function call) ---")

    config = ConfigManager()

    db_path = config.get('DATABASE_URL')
    generated_images_dir = config.get('GENERATED_IMAGES_DIR')
    log_dir = config.get('LOG_DIR')
    log_archive_dir = config.get('LOG_ARCHIVE_DIR')
    conversation_feed_json_path = config.get('WEBSITE_EXPORT_JSON_PATH') # Get the path to the JSON file

    def _delete_database_files(db_file_url: str):
        log.info(f"Attempting to delete database files for: {db_file_url}")
        try:
            parsed_url = urllib.parse.urlparse(db_file_url)
            print()
            print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            print(db_file_url)
            print(parsed_url)
            print()
            actual_db_file_path = urllib.parse.unquote(parsed_url.path)

            db_files_to_delete = [
                actual_db_file_path,
                actual_db_file_path + '-shm',
                actual_db_file_path + '-wal'
            ]

            deleted_count = 0
            for f_path in db_files_to_delete:
                if os.path.exists(f_path):
                    os.remove(f_path)
                    log.info(f"Deleted database file: {f_path}")
                    deleted_count += 1
                else:
                    log.debug(f"Database file not found (skipping): {f_path}")
            
            if deleted_count == 0:
                log.warning("No database files found to delete.")
            else:
                log.info("Database files deletion complete.")
        except Exception as e:
            log.error(f"Error deleting database files: {e}")

    def _empty_and_recreate_directory(directory_path: str):
        log.debug(f"DEBUGGING PATH: os.path.exists check for: '{directory_path}'")
        log.info(f"Attempting to empty directory: {directory_path}")
        if os.path.exists(directory_path):
            try:
                for item in os.listdir(directory_path):
                    item_path = os.path.join(directory_path, item)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.remove(item_path)
                        log.debug(f"Deleted file: {item_path}")
                log.info(f"Directory '{directory_path}' emptied.")
            except Exception as e:
                log.error(f"Error emptying directory '{directory_path}': {e}")
        else:
            log.warning(f"Directory not found (skipping emptying): {directory_path}")

        if not os.path.exists(directory_path):
            try:
                os.makedirs(directory_path, exist_ok=True)
                log.info(f"Recreated directory: {directory_path}")
            except Exception as e:
                log.error(f"Error recreating directory '{directory_path}': {e}")

    _delete_database_files(db_path)
    
    # NEW: Explicitly delete the conversation_feed.json file
    if os.path.exists(conversation_feed_json_path):
        try:
            os.remove(conversation_feed_json_path)
            log.info(f"Deleted conversation feed JSON file: {conversation_feed_json_path}")
        except Exception as e:
            log.error(f"Error deleting conversation feed JSON file '{conversation_feed_json_path}': {e}")
    else:
        log.debug(f"Conversation feed JSON file not found (skipping deletion): {conversation_feed_json_path}")


    _empty_and_recreate_directory(generated_images_dir)
    _empty_and_recreate_directory(log_dir)
    _empty_and_recreate_directory(log_archive_dir)

    log.info("--- BitWit.AI Application Reset Complete (via function call) ---")

# This block is for when reset_app.py is run directly, not through the API server.
if __name__ == "__main__":
    setup_logging(log_level=logging.INFO)

    log.info("--- Starting BitWit.AI Application Reset (direct script execution) ---")

    config = ConfigManager()

    db_path = config.get('DATABASE_PATH')
    generated_images_dir = config.get('GENERATED_IMAGES_DIR')
    log_dir = config.get('LOG_DIR')
    log_archive_dir = config.get('LOG_ARCHIVE_DIR')
    conversation_feed_json_path = config.get('WEBSITE_EXPORT_JSON_PATH') # Get the path to the JSON file

    _delete_database_files(db_path)
    
    # NEW: Explicitly delete the conversation_feed.json file in direct execution
    if os.path.exists(conversation_feed_json_path):
        try:
            os.remove(conversation_feed_json_path)
            log.info(f"Deleted conversation feed JSON file: {conversation_feed_json_path}")
        except Exception as e:
            log.error(f"Error deleting conversation feed JSON file '{conversation_feed_json_path}': {e}")
    else:
        log.debug(f"Conversation feed JSON file not found (skipping deletion): {conversation_feed_json_path}")

    _empty_and_recreate_directory(generated_images_dir)
    _empty_and_recreate_directory(log_dir)
    _empty_and_recreate_directory(log_archive_dir)

    log.info("--- BitWit.AI Application Reset Complete (direct script execution) ---")

