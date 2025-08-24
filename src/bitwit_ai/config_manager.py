# src/bitwit_ai/config_manager.py

import os
from dotenv import load_dotenv, set_key
import logging
from typing import Any, Dict
# Correct import path based on the provided project tree:
from configs.model_definitions import MODEL_DEFINITIONS

log = logging.getLogger(__name__)

class ConfigManager:
    """Gestiona las configuraciones de la aplicación, cargando desde .env y permitiendo actualizaciones."""
    _instance = None
    _config = {}
    _env_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Carga la configuración desde .env y establece valores predeterminados."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        self._env_path = os.path.join(project_root, '.env')
        
        if not os.path.exists(self._env_path):
            log.warning(f".env file not found at {self._env_path}. Using default values only.")
        else:
            load_dotenv(dotenv_path=self._env_path)
            log.info(f"Loaded .env from: {self._env_path}")

        self._config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')
        if not self._config['GEMINI_API_KEY']:
            log.error("GEMINI_API_KEY is not set in .env. Some AI features may not work.")

        # Construir la URL completa de SQLAlchemy aquí
        # db_file_path DEBE ser solo la ruta ABSOLUTA del archivo, SIN el prefijo 'sqlite:////'
        db_file_path = os.path.abspath(os.getenv('DATABASE_URL', os.path.join(project_root, 'data', 'ai_journey.db')))
        #self._config['DATABASE_URL'] = f"sqlite:////{db_file_path}" # Añadir el prefijo aquí
        self._config['DATABASE_URL'] = os.getenv('DATABASE_URL')
        log.info(f"Database URL configured as: {self._config['DATABASE_URL']}")


        self._config['BOT_PERSONALITIES_DIR'] = os.path.abspath(os.getenv('BOT_PERSONALITIES_DIR', os.path.join(project_root, 'library', 'personalities')))
        self._config['GENERATED_IMAGES_DIR'] = os.path.abspath(os.getenv('GENERATED_IMAGES_DIR', os.path.join(project_root, 'generated_images')))
        self._config['LOG_DIR'] = os.path.abspath(os.getenv('LOG_DIR', os.path.join(project_root, 'logs')))
        self._config['LOG_ARCHIVE_DIR'] = os.path.abspath(os.getenv('LOG_ARCHIVE_DIR', os.path.join(project_root, 'logs_archive')))
        self._config['WEBSITE_EXPORT_JSON_PATH'] = os.path.abspath(os.getenv('WEBSITE_EXPORT_JSON_PATH', os.path.join(project_root, 'bitwit_website', 'build', 'conversation_feed.json')))
        self._config['WEBSITE_IMAGES_WEB_PATH'] = os.path.abspath(os.getenv('WEBSITE_IMAGES_WEB_PATH', os.path.join(project_root, 'bitwit_website', 'build', 'generated_images')))


        self._config['TELEGRAM_BITWIT_TOKEN'] = os.getenv('TELEGRAM_BITWIT_TOKEN')
        self._config['TELEGRAM_VERITAS_TOKEN'] = os.getenv('TELEGRAM_VERITAS_TOKEN')
        self._config['TELEGRAM_CHANNEL_ID'] = os.getenv('TELEGRAM_CHANNEL_ID')
        self._config['TELEGRAM_BITWIT_USERNAME'] = os.getenv('TELEGRAM_BITWIT_USERNAME')
        self._config['TELEGRAM_VERITAS_USERNAME'] = os.getenv('TELEGRAM_VERITAS_USERNAME')

        self._config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'INFO').upper()

        # Configuración para habilitar/deshabilitar la escritura en la base de datos
        self._config['ENABLE_WRITE_DATABASE'] = os.getenv('ENABLE_WRITE_DATABASE', 'True').lower() == 'true'
        self._config['ENABLE_READ_DATABASE'] = os.getenv('ENABLE_READ_DATABASE', 'True').lower() == 'true'
        self._config['ENABLE_BITWIT_RUN'] = os.getenv('ENABLE_BITWIT_RUN', 'True').lower() == 'true' # Añadido
        self._config['ENABLE_X'] = os.getenv('ENABLE_X', 'False').lower() == 'true' # Añadido
        self._config['ENABLE_TELEGRAM_ALERTS'] = os.getenv('ENABLE_TELEGRAM_ALERTS', 'False').lower() == 'true' # Añadido

        # Configuración para la generación de imágenes
        self._config['ENABLE_IMAGE_GENERATION'] = os.getenv('ENABLE_IMAGE_GENERATION', 'True').lower() == 'true'
        self._config['IMAGE_GENERATION_CHANCE'] = float(os.getenv('IMAGE_GENERATION_CHANCE', 0.5))

        # Configuración de evolución de la conversación
        self._config['TOPIC_ITERATION_LIMIT'] = int(os.getenv('TOPIC_ITERATION_LIMIT', 3))
        self._config['REPLY_CHANCE'] = float(os.getenv('REPLY_CHANCE', 0.3))

        # NUEVA CONFIGURACIÓN: Habilitar/Deshabilitar Mocks para Gemini
        self._config['ENABLE_MOCKS'] = os.getenv('ENABLE_MOCKS', 'True').lower() == 'true' # Valor predeterminado a True

        # Configuración de modelos (desde model_definitions.py)
        self._config['GEMINI_TEXT_MODEL'] = os.getenv('GEMINI_TEXT_MODEL', MODEL_DEFINITIONS['gemini-2.0-flash']['name'])
        self._config['IMAGEN_IMAGE_MODEL'] = os.getenv('IMAGEN_IMAGE_MODEL', MODEL_DEFINITIONS['imagen-3.0-generate-002']['name'])
        self._config['IMAGE_MODEL_BASE_URL'] = os.getenv('IMAGE_MODEL_BASE_URL', MODEL_DEFINITIONS['imagen-3.0-generate-002']['base_url'])

        # Configuración de idioma
        self._config['BITWIT_LANGUAGE'] = os.getenv('BITWIT_LANGUAGE', 'en').lower()  # Valor predeterminado a 'en' (inglés)
        log.info(f"Language set to: {self._config['BITWIT_LANGUAGE']}")
        
        log.info("Configuration loaded.")
        log.debug(f"Current config: {self._config}")


    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración por clave."""
        return self._config.get(key, default)

    def update_config(self, new_settings: Dict[str, Any]):
        """
        Actualiza los valores de configuración en memoria y en el archivo .env.
        Solo actualiza las claves que ya existen en la configuración cargada.
        """
        if not self._env_path or not os.path.exists(self._env_path):
            log.error("Cannot update .env: .env file path not found or does not exist.")
            raise FileNotFoundError("Cannot update .env: .env file path not found.")

        updated_keys = []
        for key, value in new_settings.items():
            if key in self._config:
                # Type conversion for saving to .env (all values are strings)
                if isinstance(value, bool):
                    env_value = str(value).upper()
                elif isinstance(value, (int, float)):\
                    env_value = str(value)
                else:
                    env_value = str(value)

                self._config[key] = value
                
                set_key(self._env_path, key, env_value)
                updated_keys.append(key)
                log.info(f"Updated config key '{key}' to '{value}' and saved to .env")
            else:
                log.warning(f"Attempted to update non-existent config key: '{key}'. Skipping.")
        
        if not updated_keys:
            log.info("No valid configuration keys were updated.")
        else:
            log.info(f"Configuration update complete. Keys updated: {', '.join(updated_keys)}")

    def __getattr__(self, name):
        """Permite acceder a la configuración como config.KEY_NAME"""
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

