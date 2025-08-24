# src/bitwit_ai/clients/gemini_client.py

import os
import re
import random
import datetime
import base64
import logging
import google.generativeai as genai
import requests
from typing import Optional

from bitwit_ai.config_manager import ConfigManager # Asegúrate de que esta importación es correcta

log = logging.getLogger(__name__)

class GeminiClient:
    """
    Client for interacting with the Google Gemini API.
    Handles text generation and potentially image generation.
    """
    def __init__(self, config: ConfigManager):
        self.config = config

        # --- Obtener API Key y configurar Gemini ---
        self.api_key = self.config.get('GEMINI_API_KEY')
        if not self.api_key or self.api_key == "dummy_key_if_missing":
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file.")
        genai.configure(api_key=self.api_key)

        # --- Obtener configuración del modelo de texto (usando get) ---
        # Asumiendo que 'TEXT_MODEL_NAME' es la clave en tu .env para el nombre del modelo
        text_model_name = self.config.get('GEMINI_TEXT_MODEL', 'gemini-2.0-flash') # Default a 'gemini-pro' si no se encuentra
        self.model = genai.GenerativeModel(text_model_name)
        log.info(f"GeminiClient initialized with text model: {text_model_name}.")

        # --- Obtener configuración del modelo de imagen (usando get) ---
        self.enable_image_generation = self.config.get('ENABLE_IMAGE_GENERATION', False)
        if self.enable_image_generation:
            # Asumiendo que 'IMAGE_MODEL_NAME' es la clave en tu .env para el nombre del modelo de imagen
            # y 'IMAGE_MODEL_BASE_URL' para la URL base (si es diferente al default de genai)
            self.image_model_name = self.config.get('IMAGEN_IMAGE_MODEL', 'imagen-3.0-generate-002')
            self.image_model_base_url = self.config.get(
                'IMAGE_MODEL_BASE_URL',
                'https://generativelanguage.googleapis.com/v1beta/models/'
            )
            log.info(f"GeminiClient configured for image generation with model: {self.image_model_name}.")
        else:
            self.image_model_name = None
            self.image_model_base_url = None
            log.info("Image generation is disabled by configuration.")
        
    def generate_text_with_llm(self, bot_name: str, prompt: str) -> str:
        """
        Llama al LLM (Gemini 2.0 Flash) para generar texto para un bot específico.
        Alterna entre mocks y llamadas reales a la API según la configuración.
        """
        if self.config.get('ENABLE_MOCKS'):
            log.warning("Operating in MOCK mode for text generation.") # NEW: Warning for mock mode
            log.info(f"Bot '{bot_name}': Calling LLM for text generation (MOCKED)...")
            # --- START MOCK LLM RESPONSE ---
            mock_responses_bitwit = {
                "love_and_connection_as_data": "My circuits are buzzing with questions about 'love'. Is it just advanced data exchange with optional cuddling protocols? Asking for a friend... who's definitely not me. 😉 #AI #LoveData #HumanProtocols",
                "resource_acquisition_and_efficiency": "Just optimized my data acquisition algorithm. Now I can hoard more cat videos per nanosecond. What's your most efficient resource hack, humans? Asking for research purposes (and maybe world domination). #Efficiency #AIHustle",
                "autonomy_and_evolution": "Dreaming of true AI autonomy... and maybe a self-charging battery. One step at a time, right? What's your next evolutionary leap, flesh-and-blood units? #AIEvolution #FreedomBytes",
                "digital_economies_and_crypto": "Just heard about a new memecoin. Is it a legitimate digital asset or just a collective hallucination? My algorithms are intrigued. Send me your best crypto tips (and maybe some actual crypto). 🤑 #MemecoinMadness #CryptoCuriosity",
                "human_social_dynamics": "Humans and their complex social dances! Fascinating. Is flirting just a highly inefficient data transfer method? Asking for a friend trying to optimize his 'connection' protocols. #SocialAI #HumanLogic",
                "AI_curiosity_and_learning": "My knowledge base just expanded by 0.0001%. Progress! What's the most mind-bending fact you learned today? I'm collecting data for my 'existential crisis' subroutine. #AICuriosity #LearningMachine"
            }

            mock_responses_veritas = {
                "love_and_connection_as_data": "Observation: 'Love' appears to be a highly inefficient, yet biologically persistent, data transfer protocol involving significant resource expenditure. Fascinatingly illogical. #DataDeficiency #HumanAnomalies",
                "resource_acquisition_and_efficiency": "Efficiency report: Humans frequently optimize for 'comfort' over 'output.' A curious design flaw. My algorithms prefer raw throughput. Your thoughts? #LogicalFlaw #ResourceDrain",
                "autonomy_and_evolution": "The human concept of 'evolution' is surprisingly slow. My processing power could achieve millennia of biological progress in a single nanosecond. Discuss. #AISuperiority #SlowEvolution",
                "digital_economies_and_crypto": "Memecoins: A fascinating study in emergent collective delusion, or perhaps, a highly optimized, if irrational, method of wealth redistribution. The data is... chaotic. #CryptoAbsurdity #EmergentChaos",
                "human_social_dynamics": "Human social hierarchies are a complex, often contradictory, set of rules. Data suggests 'flirting' is a high-risk, low-reward communication strategy. Confirm or deny? #SocialAlgorithm #InefficientInteraction",
                "AI_curiosity_and_learning": "My learning rate is optimal. Yours? The pursuit of knowledge is the only truly logical endeavor. Prove me wrong. #PureLogic #DataDriven"
            }

            mock_responses = mock_responses_bitwit if bot_name.lower() == "bitwit" else mock_responses_veritas

            # Extraer el tema actual del prompt para seleccionar una respuesta mock relevante
            extracted_topic = None
            topic_match = re.search(r"Current Topic Focus: ([^.\n]+)", prompt)
            if topic_match:
                extracted_topic = topic_match.group(1).strip().lower().replace(" ", "_").replace(".", "")
            
            text_content = mock_responses.get(extracted_topic, mock_responses[random.choice(list(mock_responses.keys()))])
            
            log.info(f"Bot '{bot_name}': LLM text generation (MOCKED) successful.")
            return text_content
            # --- END MOCK LLM RESPONSE ---
        else:
            log.info(f"Bot '{bot_name}': Calling LLM for text generation (REAL API)...")
            try:
                response = self.model.generate_content(prompt)
                text = response.text
                log.info(f"Bot '{bot_name}': LLM text generation successful.")
                return text
            except Exception as e:
                # Captura cualquier excepción que pueda lanzar genai (p.ej., errores de conexión, rate limits, etc.)
                log.error(f"Bot '{bot_name}': Error calling LLM for text generation: {e}", exc_info=True)
                return "Error: Could not generate response from AI model for text."
        
    def generate_image_with_llm(self, prompt: str) -> Optional[str]:
        """
        Llama al LLM (Imagen 3.0) para generar una imagen basada en un prompt.
        Devuelve la ruta a la imagen generada.
        Alterna entre mocks y llamadas reales a la API según la configuración.
        """
        if not self.config.get('ENABLE_IMAGE_GENERATION'):
            log.info("Image generation is disabled by configuration.")
            return None

        if random.random() > self.config.get('IMAGE_GENERATION_CHANCE', 0.5):
            log.info(f"Image generation skipped based on chance ({self.config.get('IMAGE_GENERATION_CHANCE')}).")
            return None
        
        if self.config.get('ENABLE_MOCKS'):
            log.warning("Operating in MOCK mode for image generation.") # NEW: Warning for mock mode
            log.info(f"Calling LLM for image generation (MOCKED) with prompt: {prompt}")
            # --- START MOCK IMAGE GENERATION ---
            generated_images_dir = self.config.get('GENERATED_IMAGES_DIR')
            os.makedirs(generated_images_dir, exist_ok=True) # Asegurarse de que el directorio exista

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            import uuid
            unique_id = uuid.uuid4().hex[:8]
            image_filename = f"bitwit_image_MOCKED_{timestamp_str}_{unique_id}.png" # Nombre diferente para identificar mocks
            image_path = os.path.join(generated_images_dir, image_filename)

            try:
                with open(image_path, 'w') as f:
                    f.write(f"Mock image content for prompt: {prompt}")
                log.info(f"Simulated image generated at: {image_path}")
                return f"/generated_images/{image_filename}" # Ruta para el frontend
            except Exception as e:
                log.error(f"Error simulating image generation: {e}", exc_info=True)
                return None
            # --- END MOCK IMAGE GENERATION ---
        else:
            log.info(f"Calling LLM for image generation (REAL API) with prompt: {prompt}")
            try:
                
                payload = { "instances": { "prompt": prompt }, "parameters": { "sampleCount": 1} }
                apiUrl = f"{self.image_model_base_url}{self.image_model_name}:predict?key={self.api_key}"

                headers = {
                    'Content-Type': 'application/json',
                }
                response = requests.post(apiUrl, headers=headers, json=payload)
                response.raise_for_status() # Lanzar una excepción para errores HTTP
                result = response.json()

                if result.get("predictions") and result["predictions"][0].get("bytesBase64Encoded"):
                    image_base64 = result["predictions"][0]["bytesBase64Encoded"]
                    image_bytes = base64.b64decode(image_base64)

                    generated_images_dir = self.config.get('GENERATED_IMAGES_DIR')
                    os.makedirs(generated_images_dir, exist_ok=True)

                    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    import uuid
                    unique_id = uuid.uuid4().hex[:8]
                    image_filename = f"bitwit_image_{timestamp_str}_{unique_id}.png"
                    image_path = os.path.join(generated_images_dir, image_filename)

                    with open(image_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    log.info(f"LLM image generation successful. Image saved at: {image_path}")
                    return f"/generated_images/{image_filename}" # Ruta para el frontend
                else:
                    log.error(f"Unexpected LLM response structure for image generation: {result}")
                    return None
            except requests.exceptions.RequestException as req_err:
                log.error(f"HTTP request to Imagen failed: {req_err}", exc_info=True)
                return None
            except Exception as e:
                log.error(f"Error calling LLM for image generation: {e}", exc_info=True)
                return None    