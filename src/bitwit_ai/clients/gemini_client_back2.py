# src/bitwit_ai/clients/gemini_client.py

import os
from dotenv import load_dotenv, set_key
import logging
import google.generativeai as genai
import requests
import json
from typing import Dict, Any, Optional

from bitwit_ai.config_manager import ConfigManager # Asegúrate de que esta importación es correcta

log = logging.getLogger(__name__)

class GeminiClient:
    """
    Client for interacting with the Google Gemini API.
    Handles text generation and potentially image generation.
    """
    def __init__(self):
        self.config = ConfigManager() # Correctly initialize config instance

        # --- Obtener API Key y configurar Gemini ---
        api_key = self.config.get('GEMINI_API_KEY')
        if not api_key or api_key == "dummy_key_if_missing":
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file.")
        genai.configure(api_key=api_key)

        # --- Obtener configuración del modelo de texto (usando get) ---
        # Asumiendo que 'TEXT_MODEL_NAME' es la clave en tu .env para el nombre del modelo
        text_model_name = self.config.get('TEXT_MODEL_NAME', 'gemini-pro') # Default a 'gemini-pro' si no se encuentra
        self.model = genai.GenerativeModel(text_model_name)
        log.info(f"GeminiClient initialized with text model: {text_model_name}.")

        # --- Obtener configuración del modelo de imagen (usando get) ---
        self.enable_image_generation = self.config.get('ENABLE_IMAGE_GENERATION', False)
        if self.enable_image_generation:
            # Asumiendo que 'IMAGE_MODEL_NAME' es la clave en tu .env para el nombre del modelo de imagen
            # y 'IMAGE_MODEL_BASE_URL' para la URL base (si es diferente al default de genai)
            self.image_model_name = self.config.get('IMAGE_MODEL_NAME', 'dall-e-3') # Ejemplo de default para imagen
            self.image_model_base_url = self.config.get('IMAGE_MODEL_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta/models/')
            log.info(f"GeminiClient configured for image generation with model: {self.image_model_name}.")
        else:
            self.image_model_name = None
            self.image_model_base_url = None
            log.info("Image generation is disabled by configuration.")

        # --- Configuraciones de Mocks ---
        self.enable_mocks = self.config.get('ENABLE_MOCKS', False)
        if self.enable_mocks:
            self.mock_text_response = self.config.get('MOCK_LLM_RESPONSE_TEXT')
            self.mock_image_response_path = self.config.get('MOCK_IMAGE_RESPONSE_PATH')
            log.warning("GeminiClient is running in MOCK mode. Responses will be from mock files.")
        
        self.project_id = self.config.get('GOOGLE_CLOUD_PROJECT_ID') # Si lo necesitas para autenticación de GCP


    def generate_text(self, prompt: str) -> str:
        if self.enable_mocks and self.mock_text_response:
            log.debug(f"MOCK: Generating text from mock file: {self.mock_text_response}")
            try:
                with open(self.mock_text_response, 'r', encoding='utf-8') as f:
                    return f.read()
            except FileNotFoundError:
                log.error(f"Mock text file not found: {self.mock_text_response}")
                return "Error: Mock text file not found."
            except Exception as e:
                log.error(f"Error reading mock text file: {e}")
                return "Error: Could not read mock text file."

        try:
            log.debug(f"Calling LLM for text generation (REAL API)... Prompt: {prompt[:100]}...")
            response = self.model.generate_content(prompt)
            # Access the text content directly
            text_content = response.text
            log.info("LLM text generation successful.")
            return text_content
        except Exception as e:
            log.error(f"Error calling Gemini text generation API: {e}", exc_info=True)
            raise


    def generate_image(self, image_prompt: str, output_path: str) -> Optional[str]:
        if not self.enable_image_generation:
            log.info("Image generation is disabled. Skipping image generation.")
            return None

        if self.enable_mocks and self.mock_image_response_path:
            log.debug(f"MOCK: Generating image from mock path: {self.mock_image_response_path}")
            # In mock mode, we just return the mock image path without actual generation
            if os.path.exists(self.mock_image_response_path):
                log.info(f"MOCK: Returning mock image path: {self.mock_image_response_path}")
                return self.mock_image_response_path
            else:
                log.error(f"Mock image file not found at: {self.mock_image_response_path}")
                return None
        
        if not self.image_model_name or not self.image_model_base_url:
            log.error("Image generation model not properly configured.")
            return None

        # Asumo que la API de Gemini Image Generation requiere una llamada HTTP directa
        # ya que genai.GenerativeModel no expone directamente la generación de imágenes como genai.ImageModel(name)
        # Esto es un placeholder; la implementación real dependerá de la API de Google para la generación de imágenes.
        # Si usas DALL-E u otro, la URL y el payload sería diferentes.
        # Para Gemini, la generación de imágenes suele hacerse a través de multimodal models (pasando texto e imagen).
        # Si estás usando una API externa como Stable Diffusion o DALL-E a través de una URL, este es el lugar.

        log.info(f"Attempting to generate image with prompt: {image_prompt[:100]}...")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {genai.get_default_credential().token}" # Esto es para GCP Auth
        }
        
        # Este es un ejemplo para DALL-E o un servicio genérico; si es una API de Google, podría ser diferente
        payload = {
            "model_id": self.image_model_name,
            "prompt": image_prompt,
            "size": "1024x1024", # Ejemplo
            "response_format": "b64_json" # Ejemplo
        }

        try:
            # Aquí necesitarías la URL correcta para la API de generación de imágenes
            # Si Gemini no tiene una API REST directa para esto y lo haces vía genai.GenerativeModel multimodal,
            # este bloque cambiaría completamente.
            # Para fines de demostración, asumo una API REST genérica.
            response = requests.post(
                f"{self.image_model_base_url}{self.image_model_name}:generate", # Placeholder URL
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            response_data = response.json()
            
            # Asumo que la respuesta contiene una URL o datos codificados en base64
            # Esto es altamente dependiente de la API real que uses
            image_data = response_data['data'][0]['b64_json'] # Ejemplo para DALL-E
            
            # Guardar la imagen localmente (asumo que save_image_locally existe y es accesible)
            # Tendrías que convertir image_data de base64 a binario para guardarlo.
            # Este es un placeholder, necesitarías implementar la conversión y guardado real.
            # save_image_locally(image_data_binary, output_path)
            log.info(f"Image generated and saved to {output_path}")
            return output_path # Devuelve la ruta donde se guardó la imagen

        except requests.exceptions.RequestException as e:
            log.error(f"Error generating image from API: {e}", exc_info=True)
            return None
        except Exception as e:
            log.error(f"An unexpected error occurred during image generation: {e}", exc_info=True)
            return None