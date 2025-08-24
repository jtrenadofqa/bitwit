# src/bitwit_ai/utilities/reset_app.py

import os
import sys # NEW: Import sys
import shutil
import logging
import urllib.parse

# NEW: Add the project's 'src' directory to sys.path
# This allows the script to find 'bitwit_ai' package when run directly
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up three levels: utilities -> bitwit_ai -> src -> project_root
project_root = os.path.abspath(os.path.join(current_script_dir, '..', '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
    # log.debug(f"Added {src_path} to sys.path for direct script execution.") # Use log after setup


# Import ConfigManager to get paths
from bitwit_ai.config_manager import ConfigManager
# Import setup_logging to ensure this script also logs its actions
from bitwit_ai.utilities.file_utils import setup_logging

# Setup a logger for this script (needs to be done after setup_logging is imported)
log = logging.getLogger(__name__) # This will now use the logging setup from file_utils


def reset_database(db_path: str):
    """
    Deletes the database file and its associated journal/WAL files.
    It robustly extracts the file path from the SQLAlchemy URL.
    """
    log.info(f"Attempting to reset database at: {db_path}")
    try:
        parsed_url = urllib.parse.urlparse(db_path)
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
            log.info("Database reset complete.")

    except Exception as e:
        log.error(f"Error resetting database: {e}")

def empty_directory(directory_path: str, recreate: bool = True):
    """
    Empties a directory by deleting all its contents (files and subdirectories).
    If recreate is True, it ensures the directory itself exists afterwards.
    """
    log.info(f"Attempting to empty directory: {directory_path}")
    if os.path.exists(directory_path):
        try:
            for item in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                    log.debug(f"Deleted file: {item_path}")
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    log.debug(f"Deleted directory: {item_path}")
            log.info(f"Directory '{directory_path}' emptied.")
        except Exception as e:
            log.error(f"Error emptying directory '{directory_path}': {e}")
    else:
        log.warning(f"Directory not found (skipping emptying): {directory_path}")

    if recreate and not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path, exist_ok=True)
            log.info(f"Recreated directory: {directory_path}")
        except Exception as e:
            log.error(f"Error recreating directory '{directory_path}': {e}")


if __name__ == "__main__":
    # Setup logging for the reset script itself
    # Use INFO level for this script by default, to see its actions clearly
    setup_logging(log_level=logging.INFO)

    log.info("--- Starting BitWit.AI Application Reset ---")

    config = ConfigManager()

    db_path = config.get('DATABASE_PATH')
    generated_images_dir = config.get('GENERATED_IMAGES_DIR')
    log_dir = config.get('LOG_DIR')
    log_archive_dir = config.get('LOG_ARCHIVE_DIR')

    reset_database(db_path)
    empty_directory(generated_images_dir)
    empty_directory(log_dir)
    empty_directory(log_archive_dir)

    log.info("--- BitWit.AI Application Reset Complete ---")

