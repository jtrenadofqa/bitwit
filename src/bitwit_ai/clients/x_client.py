# src/bitwit_ai/clients/x_client.py

import os
import logging
import tweepy
from typing import Optional, List, Tuple, Any
from bitwit_ai.config_manager import ConfigManager # Import ConfigManager para obtener la configuración

log = logging.getLogger(__name__)

class XClient:
    """
    Cliente para interactuar con la API de X (anteriormente Twitter).
    Maneja la autenticación, el envío de tweets y la subida de medios.
    Utiliza Tweepy para las interacciones con la API.
    """
    def __init__(self, config_manager: ConfigManager):
        """
        Inicializa el XClient.
        :param config_manager: Una instancia de ConfigManager para recuperar la configuración de X.
        """
        self.config = config_manager
        self.api_key = self.config.get('X_API_KEY')
        self.api_secret = self.config.get('X_API_SECRET')
        self.access_token = self.config.get('X_ACCESS_TOKEN')
        self.access_token_secret = self.config.get('X_ACCESS_TOKEN_SECRET')
        self.enable_x = self.config.get('ENABLE_X', False) # Por defecto, deshabilitado

        self.api_v1: Optional[tweepy.API] = None
        self.client_v2: Optional[tweepy.Client] = None

        if not self.enable_x:
            log.info("La publicación en X está deshabilitada por configuración. El cliente no se inicializará.")
            return

        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            log.warning("Faltan credenciales de la API de X (API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET) en .env. La publicación en X estará deshabilitada.")
            self.enable_x = False # Deshabilitar si faltan credenciales
            return

        try:
            # Autenticación para la API v1.1 (necesaria para la subida de medios)
            auth = tweepy.OAuth1UserHandler(self.api_key, self.api_secret, self.access_token, self.access_token_secret)
            self.api_v1 = tweepy.API(auth)

            # Cliente para la API v2 (para la creación de tweets)
            self.client_v2 = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret
            )
            log.info("Clientes de la API de X inicializados correctamente.")
        except tweepy.TweepyException as e:
            log.error(f"Error al inicializar los clientes de la API de X (TweepyException): {e}")
            self.enable_x = False # Deshabilitar si falla la inicialización
        except Exception as e:
            log.error(f"Ocurrió un error inesperado al inicializar los clientes de la API de X: {e}")
            self.enable_x = False # Deshabilitar si falla la inicialización

    def _check_enabled_and_clients(self) -> bool:
        """Comprueba si la publicación en X está habilitada y los clientes están inicializados."""
        if not self.enable_x:
            log.debug("La publicación en X está deshabilitada. Saltando operación.")
            return False
        if not self.api_v1 or not self.client_v2:
            log.error("Los clientes de la API de X no están inicializados. No se puede realizar la operación.")
            return False
        return True

    def upload_media(self, image_bytes: bytes) -> Optional[str]:
        """
        Sube datos de imagen a la API de medios de X y devuelve el media_id.
        Esto utiliza la API v1.1, ya que la v2 no tiene un endpoint directo de subida de medios.
        :param image_bytes: Los bytes brutos de la imagen (por ejemplo, PNG, JPEG).
        :return: El media_id si tiene éxito, None en caso contrario.
        """
        if not self._check_enabled_and_clients():
            return None

        if not image_bytes:
            log.warning("No se proporcionaron bytes de imagen para la subida de medios.")
            return None

        try:
            # tweepy.API.media_upload puede tomar un objeto de archivo o bytes, pero es más directo
            # usar un objeto de archivo en memoria para simular un archivo.
            # Sin embargo, la implementación de Tweepy para media_upload con 'file' es flexible.
            # Aquí, pasamos el nombre de archivo y el objeto de archivo en memoria.
            # El nombre de archivo es solo un metadato para la API.
            
            # Crear un objeto de archivo en memoria para pasar los bytes
            import io
            image_file_object = io.BytesIO(image_bytes)
            image_file_object.name = "image.png" # Nombre de archivo simulado para la API

            log.info("Intentando subir medios a X...")
            media = self.api_v1.media_upload(file=image_file_object) 
            log.info(f"Medios subidos correctamente. Media ID: {media.media_id}")
            return str(media.media_id) # Asegurarse de que sea una cadena
        except tweepy.TweepyException as e:
            log.error(f"Error al subir medios a X (TweepyException): {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    log.error(f"Respuesta de error de la API de X: {error_json}")
                except ValueError:
                    log.error(f"Respuesta bruta de la API de X: {e.response.text}")
            return None
        except Exception as e:
            log.error(f"Ocurrió un error inesperado durante la subida de medios: {e}")
            return None

    def post_tweet(self, text: str, media_ids: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        """
        Publica un tweet en X.
        :param text: El contenido del tweet.
        :param media_ids: Una lista de media_ids (cadenas) para adjuntar al tweet. Por defecto es None.
        :return: Tupla: (True si tiene éxito, False en caso contrario, y el ID del tweet si tiene éxito).
        """
        if not self._check_enabled_and_clients():
            return False, None

        if not text.strip():
            log.warning("El texto del tweet está vacío. No se puede publicar.")
            return False, None

        try:
            log.info(f"Intentando publicar tweet en X. Longitud del texto: {len(text)}. IDs de medios: {media_ids}")
            response = self.client_v2.create_tweet(text=text, media_ids=media_ids)
            tweet_id = response.data['id']
            log.info(f"Tweet publicado correctamente. ID del tweet: {tweet_id}")
            return True, str(tweet_id) # Asegurarse de que sea una cadena
        except tweepy.TweepyException as e:
            log.error(f"Error al publicar en X (TweepyException): {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    log.error(f"Respuesta de error de la API de X: {error_json}")
                except ValueError:
                    log.error(f"Respuesta bruta de la API de X: {e.response.text}")
            return False, None
        except Exception as e:
            log.error(f"Ocurrió un error inesperado al publicar en X: {e}")
            return False, None
    
    def reply_to_tweet(self, tweet_id_to_reply_to: str, text: str, media_ids: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        """
        Responde a un tweet específico en X.
        :param tweet_id_to_reply_to: El ID del tweet al que responder.
        :param text: El contenido del tweet de respuesta.
        :param media_ids: Una lista de media_ids (cadenas) para adjuntar a la respuesta. Por defecto es None.
        :return: Tupla: (True si tiene éxito, False en caso contrario, y el ID del tweet de respuesta si tiene éxito).
        """
        if not self._check_enabled_and_clients():
            return False, None

        if not tweet_id_to_reply_to or not text.strip():
            log.warning("Faltan el ID del tweet al que responder o el texto de la respuesta. No se puede responder.")
            return False, None

        try:
            log.info(f"Intentando responder al tweet ID {tweet_id_to_reply_to}. Longitud del texto: {len(text)}. IDs de medios: {media_ids}")
            response = self.client_v2.create_tweet(
                text=text,
                in_reply_to_tweet_id=tweet_id_to_reply_to,
                media_ids=media_ids
            )
            reply_tweet_id = response.data['id']
            log.info(f"Respuesta publicada correctamente. ID del tweet de respuesta: {reply_tweet_id}")
            return True, str(reply_tweet_id)
        except tweepy.TweepyException as e:
            log.error(f"Error al responder al tweet (TweepyException): {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    log.error(f"Respuesta de error de la API de X: {error_json}")
                except ValueError:
                    log.error(f"Respuesta bruta de la API de X: {e.response.text}")
            return False, None
        except Exception as e:
            log.error(f"Ocurrió un error inesperado al responder al tweet: {e}")
            return False, None
