# src/clients/gemini_client.py

import google.generativeai as genai
import logging
from bitwit_ai.config_manager import ConfigManager
import requests
import base64
import os # Make sure os is imported for potential future use or if config needs it elsewhere

log = logging.getLogger(__name__)

class GeminiClient:
    """
    Client for interacting with the Google Gemini API.
    Handles text generation and potentially image generation.
    """
    def __init__(self):
        self.config = ConfigManager() # Correctly initialize config instance
        api_key = self.config.get('GEMINI_API_KEY')
        if not api_key or api_key == "dummy_key_if_missing":
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file.")

        genai.configure(api_key=api_key)

        # Initialize text generation model
        text_model_config = self.config.get_active_text_model_config()
        self.model = genai.GenerativeModel(text_model_config['name'])
        log.info(f"GeminiClient initialized with text model: {text_model_config['name']}.")

        # Initialize image generation model attributes
        if self.config.get('ENABLE_IMAGE_GENERATION'):
            image_model_config = self.config.get_active_image_model_config()
            self.image_model_name = image_model_config.get('name')
            # Ensure image_model_base_url is 'https://generativelanguage.googleapis.com/v1beta/models/'
            # This should be configured in your model_definitions.py or similar config source
            self.image_model_base_url = image_model_config.get('base_url')
            log.info(f"GeminiClient configured for image generation with model: {self.image_model_name}.")
        else:
            self.image_model_name = None
            self.image_model_base_url = None
            log.info("Image generation is disabled by configuration.")


    def generate_text(self, prompt: str) -> str:
        """Generates text using the configured Gemini model."""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                    candidate_count=1,
                    max_output_tokens=500,
                ),
            )
            if response.text:
                return response.text
            else:
                log.warning("Gemini text generation returned no text in the response.")
                return ""
        except Exception as e:
            log.error(f"Error during Gemini text generation: {e}")
            return ""

    def generate_image(self, prompt: str) -> bytes | None:
        """
        Generates an image using the configured image generation model (Imagen API)
        via the Generative Language API endpoint, mirroring the successful version.
        :param prompt: The text prompt for image generation.
        :return: Image bytes if successful, otherwise None.
        """
        if not self.image_model_name or not self.image_model_base_url:
            log.warning("Image generation is not enabled or model not configured.")
            return None

        # Get API key from config, consistent with the class's __init__
        api_key = self.config.get('GEMINI_API_KEY')
        if not api_key:
            log.error("GEMINI_API_KEY not found in configuration. Cannot generate image.")
            return None

        # 1. Construct the correct API URL (KEY CHANGE HERE)
        # Append '?key=' directly to the URL, as seen in the working example
        # And use ':predict' instead of ':generateImage'
        full_url = f"{self.image_model_base_url}{self.image_model_name}:predict?key={api_key}"

        # 2. Adjust Headers (KEY CHANGE HERE)
        # No 'Authorization' header needed as key is in URL
        headers = {
            "Content-Type": "application/json"
        }

        # 3. Prepare the payload with the correct structure (KEY CHANGE HERE)
        # 'instances' should be an object, not an array of objects
        payload = {
            "instances": {"prompt": prompt},
            "parameters": {
                "sampleCount": 1
                # Removed 'aspectRatio' and 'size' for simplicity to match working example.
                # You can add them back if the API supports them for this endpoint
                # and you need specific dimensions/aspects.
            }
        }

        log.info(f"Attempting to generate image with Imagen at: {full_url}")
        log.debug(f"Payload for image generation: {payload}")

        try:
            response = requests.post(
                full_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

            response_json = response.json()

            # The structure of the response for Imagen is expected to be 'predictions'
            if 'predictions' in response_json and response_json['predictions']:
                # Take the first prediction and get the base64 encoded image data
                image_data_base64 = response_json['predictions'][0].get('bytesBase64Encoded')
                if image_data_base64:
                    log.info("Image bytes received and decoded successfully.")
                    return base64.b64decode(image_data_base64)
                else:
                    log.error(f"No 'bytesBase64Encoded' found in the API response from {full_url}. Response: {response_json}")
                    return None # Changed from b"" to None for consistency with type hint
            else:
                log.error(f"Unexpected image API response format from {full_url}: {response_json}")
                return None # Changed from b"" to None

        except requests.exceptions.RequestException as req_err:
            log.error(f"Network or API request error during image generation to {full_url}: {req_err}")
            if response is not None: # Ensure response exists before trying to access its attributes
                log.error(f"Response status: {response.status_code}, Response body: {response.text}")
            return None
        except ValueError as json_err:
            log.error(f"JSON decoding error from image API response from {full_url}: {json_err}. Raw response: {response.text if response else 'N/A'}")
            return None
        except Exception as e:
            log.error(f"An unexpected error occurred during image generation to {full_url}: {e}")
            return None