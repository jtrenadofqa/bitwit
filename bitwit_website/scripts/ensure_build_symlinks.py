# BitWit.AI/bitwit_website/scripts/ensure_build_symlinks.py

import os
import sys
import shutil
import logging

# Set up basic logging for this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def ensure_symlink(source_path, symlink_path):
    """
    Ensures that symlink_path exists and is a symbolic link to source_path.
    If symlink_path exists and is not a symlink, or is a broken symlink, it is removed and recreated.
    If symlink_path is a directory, its contents are removed and then it's deleted and recreated as symlink.
    """
    source_abs_path = os.path.abspath(source_path)
    symlink_abs_path = os.path.abspath(symlink_path)

    log.info(f"Attempting to ensure symlink: '{symlink_abs_path}' -> '{source_abs_path}'")

    # Check if symlink_path exists
    if os.path.exists(symlink_abs_path):
        if os.path.islink(symlink_abs_path):
            # It's a symlink, check if it points to the correct target
            current_target = os.readlink(symlink_abs_path)
            if os.path.abspath(current_target) == source_abs_path:
                log.info(f"Symlink already exists and is correct: '{symlink_abs_path}'")
                return
            else:
                log.warning(f"Existing symlink '{symlink_abs_path}' points to wrong target. Removing...")
                os.remove(symlink_abs_path)
        elif os.path.isdir(symlink_abs_path):
            log.warning(f"'{symlink_abs_path}' is a directory, not a symlink. Removing contents and then directory...")
            try:
                shutil.rmtree(symlink_abs_path) # Remove directory and its contents
            except OSError as e:
                log.error(f"Error removing directory '{symlink_abs_path}': {e}")
                sys.exit(1)
        else:
            log.warning(f"'{symlink_abs_path}' exists but is not a symlink or directory. Removing...")
            os.remove(symlink_abs_path)
    elif os.path.islink(symlink_abs_path): # Path doesn't exist, but it's a broken symlink
        log.warning(f"Broken symlink '{symlink_abs_path}' found. Removing...")
        os.remove(symlink_abs_path)

    # Now, create the symlink
    try:
        os.symlink(source_abs_path, symlink_abs_path)
        log.info(f"Successfully created symlink: '{symlink_abs_path}' -> '{source_abs_path}'")
    except OSError as e:
        log.error(f"Failed to create symlink '{symlink_abs_path}' to '{source_abs_path}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Determine paths relative to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bitwit_website_root = os.path.dirname(script_dir) # Go up from scripts/ to bitwit_website/
    project_root = os.path.dirname(bitwit_website_root) # Go up from bitwit_website/ to BitWit.AI/

    # Define source and target paths for the symlinks
    # Source: The actual generated_images directory at the project root
    source_images_dir = os.path.join(project_root, 'generated_images')
    
    # Target 1: The generated_images within the React build folder
    build_images_symlink_target = os.path.join(bitwit_website_root, 'build', 'generated_images')
    # Target 2: The generated_images within the React public folder
    public_images_symlink_target = os.path.join(bitwit_website_root, 'public', 'generated_images')

    # Ensure the source directory for images exists
    if not os.path.exists(source_images_dir):
        log.info(f"Source image directory '{source_images_dir}' does not exist. Creating it.")
        os.makedirs(source_images_dir, exist_ok=True)

    # Ensure the build directory exists (it should be created by react-scripts build)
    build_dir = os.path.join(bitwit_website_root, 'build')
    if not os.path.exists(build_dir):
        log.info(f"Build directory '{build_dir}' does not exist. Creating it.")
        os.makedirs(build_dir, exist_ok=True)

    # Ensure the public directory exists
    public_dir = os.path.join(bitwit_website_root, 'public')
    if not os.path.exists(public_dir):
        log.info(f"Public directory '{public_dir}' does not exist. Creating it.")
        os.makedirs(public_dir, exist_ok=True)

    # Ensure both symlinks are correctly set up
    ensure_symlink(source_images_dir, build_images_symlink_target)
    ensure_symlink(source_images_dir, public_images_symlink_target)

    log.info("All necessary symlinks for generated images are set up.")
