# api_server.py

import os
import sys
import logging
from typing import Optional
from flask import Flask, jsonify, request, send_from_directory, make_response
from flask_cors import CORS
from threading import Thread, Lock
import time


# Add the 'src' directory to sys.path to allow imports from bitwit_ai package
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import core components from your bitwit_ai package
from bitwit_ai.config_manager import ConfigManager
from bitwit_ai.utilities.file_utils import setup_logging, reset_application, export_conversations_to_json
from bitwit_ai.application import BitWitCoreApplication # The main application class

# --- Flask App Setup ---
# Initialize ConfigManager here to get paths
config = ConfigManager()

# Determine REACT_BUILD_DIR from config, falling back to a default if not set in .env
# This ensures consistency with how other paths are managed
REACT_BUILD_DIR = config.get('WEBSITE_EXPORT_JSON_PATH').replace('conversation_feed.json', '') # Extract build dir from json path
if not REACT_BUILD_DIR: # Fallback if config value is empty or malformed
    project_root = os.path.dirname(os.path.abspath(__file__))
    REACT_BUILD_DIR = os.path.join(project_root, 'bitwit_website', 'build')

app = Flask(__name__, static_folder=REACT_BUILD_DIR)
CORS(app)

# --- Global Application State ---
# ConfigManager is already initialized above
setup_logging(log_level=getattr(logging, config.get('LOG_LEVEL', 'INFO').upper()))
log = logging.getLogger(__name__)

# Suppress werkzeug (Flask's internal server) access logs for cleaner output
logging.getLogger('werkzeug').setLevel(logging.WARNING)

bitwit_app_instance: Optional[BitWitCoreApplication] = None
app_init_lock = Lock() # To prevent race conditions during app initialization

run_lock = Lock() # To prevent multiple BitWit run threads simultaneously

# --- Initialization Function ---
def initialize_bitwit_app():
    """Initializes the BitWitCoreApplication instance."""
    global bitwit_app_instance
    with app_init_lock:
        if bitwit_app_instance is None:
            log.info("Initializing BitWitCoreApplication for the API server...")
            try:
                # Pass the already initialized config object
                bitwit_app_instance = BitWitCoreApplication(config)
                log.info("BitWitCoreApplication initialized successfully.")
                # Ensure conversation_feed.json is generated on startup
                output_json_path = config.get('WEBSITE_EXPORT_JSON_PATH')
                web_images_dir = config.get('WEBSITE_IMAGES_WEB_PATH')
                export_conversations_to_json(bitwit_app_instance.db_manager, output_json_path, web_images_dir)
                log.info("Initial website data exported on startup.")
            except Exception as e:
                log.error(f"Failed to initialize BitWitCoreApplication: {e}", exc_info=True)
                bitwit_app_instance = None
        else:
            log.info("BitWitCoreApplication already initialized.")

# Initialize the application when Flask app context is ready
with app.app_context():
    initialize_bitwit_app()


# --- API Endpoints ---

@app.route('/api/run_bitwit', methods=['POST'])
def run_bitwit():
    """Endpoint to run the BitWit AI content generation process one or more times."""
    data = request.get_json()
    count = data.get('count', 1) # Get count from request, default to 1

    if not isinstance(count, int) or count < 1:
        return jsonify({"status": "error", "message": "Invalid run count provided."}), 400

    if run_lock.acquire(blocking=False): # Acquire lock to ensure only one run thread
        try:
            if bitwit_app_instance is None:
                log.warning("BitWitCoreApplication is not initialized. Attempting to re-initialize.")
                initialize_bitwit_app()
                if bitwit_app_instance is None:
                    return jsonify({"status": "error", "message": "BitWitCoreApplication failed to initialize."}), 500

            log.info(f"API: Received request to run BitWit {count} time(s).")
            def run_in_thread():
                """Function to run BitWit in a separate thread."""
                try:
                    for i in range(count):
                        log.info(f"Starting BitWit run {i+1} of {count}...")
                        bitwit_app_instance.run() # Call the main run method
                        log.info(f"BitWit run {i+1} completed.")
                        
                        # After each run, update website data to reflect new posts/images
                        output_json_path = config.get('WEBSITE_EXPORT_JSON_PATH')
                        web_images_dir = config.get('WEBSITE_IMAGES_DIR')
                        export_conversations_to_json(bitwit_app_instance.db_manager, output_json_path, web_images_dir)
                        log.info(f"Website data (conversation_feed.json) updated after run {i+1}.")

                        if i < count - 1: # Don't sleep after the last run
                            log.info(f"Waiting 5 seconds before next run...")
                            time.sleep(5) # Delay between runs
                    
                    log.info(f"All {count} BitWit runs completed in background thread.")

                except Exception as e:
                    log.error(f"Error during BitWit run(s) in background: {e}", exc_info=True)
                finally:
                    run_lock.release() # Release lock when thread finishes

            Thread(target=run_in_thread).start() # Start the background thread
            return jsonify({"status": "success", "message": f"BitWit run(s) started in background ({count} times)."}), 202
        except Exception as e:
            log.error(f"API: Error starting BitWit run(s): {e}", exc_info=True)
            if run_lock.locked(): # Ensure lock is released even if error occurs early
                run_lock.release()
            return jsonify({"status": "error", "message": f"Failed to start BitWit run(s): {str(e)}"}), 500
    else:
        log.warning("API: Request to run BitWit received, but another run is already in progress.")
        return jsonify({"status": "busy", "message": "Another BitWit run is already in progress. Please wait."}), 409


@app.route('/api/reset_app', methods=['POST'])
def reset_application_endpoint():
    """Endpoint to reset the application (database, images, logs)."""
    log.info("API: Received request to reset application.")
    try:
        # Before resetting and re-initializing, dispose of the current DBManager's engine
        global bitwit_app_instance
        if bitwit_app_instance and bitwit_app_instance.db_manager:
            bitwit_app_instance.db_manager.dispose()
            log.info("Disposed of old DBManager engine before reset.")

        reset_application() # Call the function from file_utils
        
        # Force re-initialization of the BitWitCoreApplication after reset
        # This will create a new DBManager instance with fresh connections
        with app_init_lock:
            bitwit_app_instance = None # Force re-initialization
        initialize_bitwit_app() # This call will also trigger export_conversations_to_json (which will be empty)

        return jsonify({"status": "success", "message": "Application reset successfully. Reloading page..."}), 200

    except Exception as e:
        log.error(f"API: Error resetting application: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Failed to reset application: {str(e)}"}), 500

@app.route('/api/update_website_data', methods=['POST'])
def update_website_data_endpoint():
    """Endpoint to manually trigger website data export."""
    log.info("API: Received request to update website data.")
    try:
        if bitwit_app_instance is None or bitwit_app_instance.db_manager is None:
            log.warning("BitWitCoreApplication or DBManager not initialized. Cannot export website data.")
            return jsonify({"status": "error", "message": "Application not ready for data export. Please run BitWit first."}), 500

        output_json_path = config.get('WEBSITE_EXPORT_JSON_PATH')
        web_images_dir = config.get('WEBSITE_IMAGES_DIR')

        if not output_json_path or not web_images_dir:
            return jsonify({"status": "error", "message": "Website export paths not configured in .env"}), 500

        success = export_conversations_to_json(
            bitwit_app_instance.db_manager,
            output_json_path,
            web_images_dir
        )
        if success:
            return jsonify({"status": "success", "message": "Website data exported successfully."}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to export website data."}), 500
    except Exception as e:
        log.error(f"API: Error updating website data: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Failed to update website data: {str(e)}"}), 500

@app.route('/api/get_config', methods=['GET'])
def get_config_endpoint():
    """Endpoint to get current configuration settings."""
    log.debug("API: Received request to get configuration.")
    try:
        return jsonify({"status": "success", "config": config._config}), 200
    except Exception as e:
        log.error(f"API: Error getting config: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Failed to retrieve config: {str(e)}"}), 500

@app.route('/api/update_config', methods=['POST'])
def update_config_endpoint():
    """Endpoint to update configuration settings."""
    log.info("API: Received request to update configuration.")
    try:
        new_settings = request.get_json()
        if not new_settings:
            return jsonify({"status": "error", "message": "No settings provided in request body."}), 400
        
        config.update_config(new_settings)
        
        # Dispose of old engine before re-initializing if config changes affect DB
        global bitwit_app_instance
        if bitwit_app_instance: # Check if instance exists before disposing
            if bitwit_app_instance.db_manager:
                bitwit_app_instance.db_manager.dispose()
                log.info("Disposed of old DBManager engine after config update.")

        with app_init_lock:
            bitwit_app_instance = None
        initialize_bitwit_app() # This call will also trigger export_conversations_to_json

        return jsonify({"status": "success", "message": "Configuration updated and saved.", "updated_config": config._config}), 200
    except Exception as e:
        log.error(f"API: Error updating config: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Failed to update config: {str(e)}"}), 500


@app.route('/api/get_logs', methods=['GET'])
def get_logs_endpoint():
    """Endpoint to get recent log entries."""
    try:
        log_file_path = os.path.join(config.get('LOG_DIR'), 'bitwit_ai.log')
        if not os.path.exists(log_file_path):
            return jsonify({"status": "success", "logs": ["No log file found yet."]})

        num_lines = request.args.get('lines', 100, type=int)
        
        logs = []
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(f.tell() - 20480, 0), os.SEEK_SET)
            lines = f.readlines()
            
            logs = [line.strip() for line in lines if line.strip()][-num_lines:]

        return jsonify({"status": "success", "logs": logs}), 200
    except Exception as e:
        log.error(f"API: Error getting logs: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Failed to retrieve logs: {str(e)}"}), 500

# --- Serve React Frontend ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    """
    Serve static files from the React build directory, or fallback to index.html
    for client-side routes.
    """
    full_path = os.path.join(app.static_folder, path)

    if path == 'conversation_feed.json' or path.startswith('generated_images/'):
        response = make_response(send_from_directory(app.static_folder, path))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return send_from_directory(app.static_folder, path)
    
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """
    Recibe los datos del webhook de Telegram y los pasa a la aplicación central.
    """
    try:
        data = request.json
        if not data:
            log.warning("Received an empty request to the Telegram webhook.")
            return jsonify({"status": "ok", "message": "Empty request"}), 200

        # Llama a la lógica de la aplicación para manejar el mensaje de Telegram
        # Importamos la aplicación global para poder llamarla
        global bitwit_app_instance 
        
        # En una ejecución real, esto debería correr en un hilo separado
        # para no bloquear la respuesta al webhook.
        thread = Thread(target=lambda: bitwit_app_instance.handle_telegram_message(data))
        thread.start()
        
        return jsonify({"status": "ok", "message": "Message received"}), 200
    except Exception as e:
        log.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to process webhook"}), 500

@app.route('/api/web-chat', methods=['POST'])
def web_chat():
    """
    Handles chat messages from the web frontend and posts them to the Telegram channel.
    """
    try:
        data = request.json
        user_message = data.get('message')
        # user_id is optional for now, but good practice to include
        user_id = data.get('user_id', 'web_user') 

        if not user_message:
            return jsonify({"error": "Missing message"}), 400
        
        # Guardar el mensaje del usuario en la base de datos de la web
        global bitwit_app_instance
        bitwit_app_instance.db_manager.save_message(user_id=str(user_id), content=user_message, is_bot=False, source='web')

        log.info(f"Received message from web: {user_message}")

        # Generar la respuesta de texto con Gemini
        # Nota: Asumo que tienes un método handle_web_message en tu clase BitWitCoreApplication
        gemini_response = bitwit_app_instance.handle_web_message(user_message)

        # Guardar la respuesta del bot en la base de datos de la web
        bitwit_app_instance.db_manager.save_message(user_id=str(user_id), content=gemini_response, is_bot=True, source='web')
        
        # Obtener el ID del canal de la configuración
        telegram_channel_id = bitwit_app_instance.config.get("TELEGRAM_CHANNEL_ID")
        
        if telegram_channel_id:
            log.info(f"Posting web response to Telegram channel {telegram_channel_id}")
            bitwit_app_instance.post_to_telegram_channel(gemini_response, telegram_channel_id)
        else:
            log.warning("Telegram channel ID not found in configuration. Skipping post to Telegram.")
        
        # Devolver la respuesta a la web
        return jsonify({"response": gemini_response}), 200

    except Exception as e:
        log.error(f"Error handling web chat request: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred"}), 500

# --- Main execution block ---
if __name__ == '__main__':
    if not os.path.exists(REACT_BUILD_DIR):
        log.warning(f"React build directory not found at {REACT_BUILD_DIR}. "
                    "Frontend might not be served correctly. Please run 'npm run build' in your React project.")
        os.makedirs(REACT_BUILD_DIR, exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=5000)
