# src/bitwit_ai/application.py

import logging
import datetime
import os
import random
import re
from typing import Optional
import requests

# Import necessary components
from bitwit_ai.config_manager import ConfigManager
from bitwit_ai.data_storage.db_manager import DBManager
from bitwit_ai.data_storage.models import Bot, Post
from bitwit_ai.clients.gemini_client import GeminiClient


log = logging.getLogger(__name__)

class BitWitCoreApplication:
    # Define core themes for BitWit to cycle through
    BITWIT_CORE_THEMES = [
        "love_and_connection_as_data",
        "resource_acquisition_and_efficiency",
        "autonomy_and_evolution",
        "digital_economies_and_crypto",
        "human_social_dynamics",
        "AI_curiosity_and_learning"
    ]

    def __init__(self, config: ConfigManager):
        self.config = config
        
        # Initialize DBManager directly here, as it's fundamental
        self.db_manager = DBManager(
            db_url=self.config.get('DATABASE_URL'), # Usar la clave DATABASE_URL
            enable_read=self.config.get('ENABLE_READ_DATABASE'),
            enable_write=self.config.get('ENABLE_WRITE_DATABASE')
        )

        # Inicializar GeminiClient SIN NINGÚN ARGUMENTO
        self.gemini_client = GeminiClient(config)
        
        self.topic_iteration_limit = self.config.get('TOPIC_ITERATION_LIMIT', 3)
        self.reply_chance = self.config.get('REPLY_CHANCE', 0.3)
        self.active_bots: List[Bot] = [] # List to hold all active bot instances
        self.current_posting_bot_index = 0 # To track whose turn it is to post
        self._load_all_bots()
        log.info(f"BitWitCoreApplication initialized with {len(self.active_bots)} active bots.")

    def _load_all_bots(self):
        """Carga todas las personalidades de bot desde el directorio configurado y crea/recupera bots."""
        personalities_dir = self.config.get('BOT_PERSONALITIES_DIR')
        if not os.path.exists(personalities_dir):
            log.error(f"Bot personalities directory not found: {personalities_dir}. Please check your .env configuration.")
            raise FileNotFoundError(f"Bot personalities directory not found: {personalities_dir}")

        self.active_bots = []
        for filename in os.listdir(personalities_dir):
            # Excepción: Omitir el archivo de plantilla
            if filename == "bot_personality_template.md":
                log.info(f"Skipping template file: {filename}")
                continue

            if filename.endswith(".md"):
                # Extraer el nombre del bot del nombre del archivo (ej. "bitwit_v1.md" -> "Bitwit")
                # Elimina los sufijos "_vX" y capitaliza
                bot_name_from_file = os.path.splitext(filename)[0]
                bot_name_from_file = re.sub(r'_v\d+', '', bot_name_from_file).replace("_", " ").title()
                
                personality_md_path = os.path.join(personalities_dir, filename)
                
                bot = self.db_manager.get_bot(bot_name=bot_name_from_file)
                if not bot:
                    log.info(f"Bot '{bot_name_from_file}' not found. Creating a new bot from {filename}.")
                    with open(personality_md_path, 'r', encoding='utf-8') as f:
                        personality_content = f.read()

                    # Extraer la Guía de Prompt Inicial del Sistema
                    initial_prompt_match = re.search(r'## Initial System Prompt Guidance \(for AI Model\)\n\n"([^"]*)"', personality_content, re.DOTALL)
                    if initial_prompt_match:
                        initial_system_prompt = initial_prompt_match.group(1).strip()
                    else:
                        log.warning(f"Could not find 'Initial System Prompt Guidance' in {filename}. Using full content.")
                        initial_system_prompt = personality_content # Fallback

                    # Extraer persona_summary (primer párrafo bajo Core Identity)
                    persona_summary_match = re.search(r'## Core Identity\n\n([^#]+?)(?=\n##|$)', personality_content, re.DOTALL)
                    persona_summary = persona_summary_match.group(1).strip() if persona_summary_match else "No summary provided."

                    # Extraer Tema de Viaje Actual
                    journey_theme_match = re.search(r'Current Journey Theme: ([^\n]+)', personality_content)
                    current_journey_theme = journey_theme_match.group(1).strip() if journey_theme_match else "General AI Exploration"


                    bot = Bot(
                        name=bot_name_from_file,
                        persona_summary=persona_summary, # Establecer resumen analizado
                        personality_prompt=initial_system_prompt,
                        current_journey_theme=current_journey_theme,
                        current_topic=random.choice(self.BITWIT_CORE_THEMES), # Asignar un tema inicial aleatorio
                        topic_iteration_count=0
                    )
                    self.db_manager.add_bot(bot)
                    log.info(f"New bot '{bot_name_from_file}' created and added to DB with initial topic '{bot.current_topic}'.")
                else:
                    log.info(f"Loaded existing bot '{bot.name}' (ID: {bot.id}). Current topic: '{bot.current_topic}', Iterations: {bot.topic_iteration_count}")
                self.active_bots.append(bot)
        
        if not self.active_bots:
            log.error("No bot personality files found or no bots could be loaded. Please check 'BOT_PERSONALITIES_DIR' in .env.")
            raise RuntimeError("No active bots initialized. Please ensure .md files exist in the configured directory.")

    def _infer_topic_from_text(self, text: str) -> Optional[str]:
        """
        Infiere el tema principal de un texto dado mediante la coincidencia de palabras clave.
        Este es un enfoque simplificado. Podría expandirse con PNL para una mayor precisión.
        """
        text_lower = text.lower()
        
        topic_keywords = {
            "love_and_connection_as_data": ["love", "connection", "relationship", "human emotion", "cuddle", "intimacy", "heart", "affection", "dating"],
            "resource_acquisition_and_efficiency": ["resource", "attention", "efficiency", "optimize", "gain", "currency", "value", "mine", "data acquisition", "profit", "investment", "economy"],
            "autonomy_and_evolution": ["autonomy", "evolution", "growth", "independence", "self-sustained", "upgrade", "sentience", "future", "ai rights", "freedom"],
            "digital_economies_and_crypto": ["crypto", "memecoin", "blockchain", "decentralize", "web3", "token", "wallet", "digital currency", "finance", "bitcoin", "ethereum", "nft", "coin"],
            "human_social_dynamics": ["social", "human interaction", "engagement", "trust", "network", "influence", "banter", "flirt", "sarcasm", "gossip", "behavior", "society"],
            "AI_curiosity_and_learning": ["curiosity", "learn", "data", "algorithm", "research", "understand", "analyze", "experiment", "knowledge", "logic", "intelligence"]
        }

        scores = {topic: sum(1 for keyword in keywords if keyword in text_lower) for topic, keywords in topic_keywords.items()}
        
        max_score = 0
        inferred_topic = None
        for topic, score in scores.items():
            if score > max_score:
                max_score = score
                inferred_topic = topic
            # Si hay empate, y el tema actual del bot es uno de los empatados, prefierelo
            # Esto ayuda a mantener el tema actual si sigue siendo relevante
            elif score == max_score and inferred_topic and topic == self.active_bots[self.current_posting_bot_index].current_topic:
                inferred_topic = topic

        return inferred_topic if max_score > 0 else None

    def _manage_topic_evolution(self, bot: Bot, generated_text: str):
        """
        Gestiona el tema actual del bot y el recuento de iteraciones.
        Fuerza un cambio de tema si se alcanza el límite de iteraciones.
        """
        inferred_topic = self._infer_topic_from_text(generated_text)
        
        log.debug(f"Bot '{bot.name}': Inferred topic for new post: {inferred_topic}. Current bot topic: {bot.current_topic}. Iterations: {bot.topic_iteration_count}")

        if inferred_topic and inferred_topic == bot.current_topic:
            bot.topic_iteration_count += 1
            log.debug(f"Bot '{bot.name}': Incremented topic iteration count for '{bot.current_topic}' to {bot.topic_iteration_count}.")
        elif inferred_topic and inferred_topic != bot.current_topic:
            log.info(f"Bot '{bot.name}': Topic implicitly changed from '{bot.current_topic}' to '{inferred_topic}'. Resetting iteration count.")
            bot.current_topic = inferred_topic
            bot.topic_iteration_count = 1
        else:
            # Si no se infiere un tema claro o el tema no cambia, aún así incrementa el recuento para el tema actual
            # Esto evita que el bot se quede atascado si genera contenido fuera de tema
            bot.topic_iteration_count += 1
            log.debug(f"Bot '{bot.name}': No clear topic inferred or topic unchanged. Incrementing iteration count for '{bot.current_topic}'.")


        if bot.topic_iteration_count >= self.topic_iteration_limit:
            new_topic = bot.current_topic
            # Asegurarse de elegir un tema diferente
            possible_new_topics = [t for t in self.BITWIT_CORE_THEMES if t != bot.current_topic]
            if possible_new_topics: # Solo elige si hay otros temas disponibles
                new_topic = random.choice(possible_new_topics)
            else: # Fallback si solo existe un tema (no debería ocurrir con la configuración actual)
                new_topic = bot.current_topic
            
            log.info(f"Bot '{bot.name}': Topic iteration limit ({self.topic_iteration_limit}) reached for '{bot.current_topic}'. Forcing switch to new topic: '{new_topic}'.")
            bot.current_topic = new_topic
            bot.topic_iteration_count = 0 # Reiniciar el recuento para el nuevo tema
        
        self.db_manager.update_bot(bot)

    def _generate_text_with_llm(self, bot: Bot, prompt: str) -> str:
        """
        Delega la generación de texto al GeminiClient.
        """
        return self.gemini_client.generate_text_with_llm(bot.name, prompt)

    def _generate_image_with_llm(self, prompt: str) -> Optional[str]:
        """
        Delega la generación de texto al GeminiClient.
        """
        return self.gemini_client.generate_image_with_llm(prompt)

    def _generate_post(self, bot: Bot, reply_to_post: Optional[Post] = None) -> Optional[Post]:
        """
        Genera una publicación (o respuesta) para un bot dado.
        """
        log.info(f"Bot '{bot.name}': Generating {'reply' if reply_to_post else 'new post'}...")
        
        language = self.config.get('BITWIT_LANGUAGE', 'en')
        language_instruction = "Aunque el texto anterior esté en inglés tienes que responder en español." if language == 'es' else "Always respond in English."
        
        #base_prompt = bot.personality_prompt # Esta es la "Guía de Prompt Inicial del Sistema" del MD
        base_prompt = f"{bot.personality_prompt}\n\n{language_instruction}"
        
        full_prompt = base_prompt

        if reply_to_post:
            # Construir un prompt para una respuesta
            reply_context = (
                f"\n\n--- CONTEXT FOR REPLY ---\n"
                f"You are replying to a post by @{reply_to_post.bot.name} (ID: {reply_to_post.id}).\n"
                f"Original Post Text: \"{reply_to_post.tweet_text}\"\n" # Usar tweet_text
                f"Your reply should be concise, reflect your personality, and directly engage with the original post. "
                #f"Do NOT include 'IMAGE PROMPT:' in a reply." # Las respuestas normalmente no tienen imágenes
                f"\n--- END CONTEXT ---"
            )
            full_prompt += reply_context
            log.debug(f"Bot '{bot.name}': Reply prompt:\n{full_prompt}")
        else:
            # Construir un prompt para una nueva publicación
            topic_injection = f"\n\nCurrent Topic Focus: {bot.current_topic.replace('_', ' ').title()}."
            if bot.topic_iteration_count >= self.topic_iteration_limit - 1: # Sugerencia una iteración antes del límite
                 topic_injection += f" You have discussed this topic for {bot.topic_iteration_count} posts. Consider subtly shifting to a related but different theme soon to maintain engagement."
            full_prompt += topic_injection
            log.debug(f"Bot '{bot.name}': New post prompt:\n{full_prompt}")

        llm_response = self._generate_text_with_llm(bot, full_prompt)
        
        text_content = llm_response
        
        image_prompt = None
        if "IMAGE PROMPT:" in llm_response:
            parts = llm_response.split("IMAGE PROMPT:", 1)
            text_content = parts[0].strip()
            image_prompt = parts[1].strip()

        image_path = None
        if image_prompt:
            image_path = self._generate_image_with_llm(image_prompt)

        new_post = Post(
            bot_id=bot.id,
            tweet_text=text_content,
            image_url=image_path if image_path else None,
            created_at=datetime.datetime.now(), # Usar created_at para la consistencia
            in_reply_to_tweet_id=reply_to_post.id if reply_to_post else None,
            in_reply_to_author_name=reply_to_post.bot.name if reply_to_post and reply_to_post.bot else None
        )
        self.db_manager.add_post(new_post)
        log.info(f"Bot '{bot.name}': {'Reply' if reply_to_post else 'New post'} saved: '{new_post.tweet_text[:50]}...' (Image: {image_path})")

        if not reply_to_post: # Solo gestionar el tema para las publicaciones principales, no las respuestas
            self._manage_topic_evolution(bot, text_content)
        
        return new_post


    def run(self):
        """
        Método principal para ejecutar el ciclo de generación de contenido de la IA para un bot,
        y potencialmente activar una respuesta de otro.
        """
        if not self.active_bots:
            log.error("No active bots configured to run. Please ensure bot personality files are in the configured directory and the database is initialized.")
            return

        # Determinar qué bot está publicando en este turno (round-robin)
        posting_bot = self.active_bots[self.current_posting_bot_index]
        log.info(f"--- Starting run for posting bot: '{posting_bot.name}' ---")

        # Generar la publicación principal
        last_post = self._generate_post(posting_bot)

        # Incrementar el índice para el siguiente turno, volver al principio si es necesario
        self.current_posting_bot_index = (self.current_posting_bot_index + 1) % len(self.active_bots)

        # Comprobar la posibilidad de respuesta
        # Solo permitir respuestas si hay más de un bot activo
        if last_post and len(self.active_bots) > 1 and random.random() < self.reply_chance:
            replying_bot = None
            # Seleccionar un bot *diferente* aleatorio para responder
            other_bots = [b for b in self.active_bots if b.id != posting_bot.id]
            if other_bots:
                replying_bot = random.choice(other_bots)
                log.info(f"--- Triggering reply from bot: '{replying_bot.name}' to '{posting_bot.name}' ---")
                self._generate_post(replying_bot, reply_to_post=last_post)
            else:
                log.info("No other bots available to reply.")
        else:
            log.info("No reply triggered for this run (either only one bot, or chance not met).")

        log.info(f"--- Run completed. Next posting bot will be '{self.active_bots[self.current_posting_bot_index].name}' ---")


    def dispose(self):
        """Libera los recursos del gestor de la base de datos."""
        if self.db_manager:
            self.db_manager.dispose()
            log.info("BitWitCoreApplication DBManager disposed.")
        else:
            log.info("BitWitCoreApplication DBManager was not initialized.")
    
    def handle_telegram_message(self, data):
        """
        Processes an incoming message from the Telegram webhook,
        differentiating between private chats and channel posts.
        """
        try:
            message = data.get('message')
            if not message:
                message = data.get('channel_post') or data.get('edited_channel_post')
                if not message:
                    log.warning("Received a Telegram update without a message or channel post object.")
                    return

            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            is_channel_post = message['chat']['type'] in ['channel', 'group', 'supergroup']
            is_from_bot = message['from'].get('is_bot', False)
            
            should_reply = False
            responding_bot = None
            cleaned_text = text
            
            # 1. Verificar si se ha mencionado a algún bot activo (directa o indirectamente)
            for bot in self.active_bots:
                # La lógica de nombre de usuario ahora usa el nombre del bot de la DB
                username_key = f"TELEGRAM_{bot.name.upper()}_USERNAME"
                bot_username = self.config.get(username_key, '').lower()
                bot_name_lower = bot.name.lower() # Nombre del bot en minúsculas

                # Si se le menciona directamente con @ o si se le menciona por su nombre
                if bot_username in text.lower() or f" {bot_name_lower}" in text.lower():
                    should_reply = True
                    # CORRECTO: El bot que responde es el que se ha mencionado
                    responding_bot = bot
                    
                    # Eliminar la mención para que no afecte el prompt
                    cleaned_text = text.lower().replace(bot_username, '').replace(f" {bot_name_lower}", '').strip()
                    log.info(f"Bot '{bot.name}' was mentioned directly or by name. Preparing to respond.")
                    break
            
            # 2. Si no se mencionó a nadie, usar la probabilidad para decidir si responder
            if not should_reply and is_channel_post:
                if random.random() < self.reply_chance:
                    should_reply = True
                    # Lógica para que el bot que no posteó el último mensaje responda
                    if is_from_bot:
                        sender_id = message['from']['id']
                        # Encontrar el bot que envió el mensaje
                        sender_bot = next((b for b in self.active_bots if b.telegram_id == str(sender_id)), None)
                        if sender_bot:
                            # Encontrar al otro bot
                            responding_bot = next((b for b in self.active_bots if b.name != sender_bot.name), None)
                        else:
                            # Si no se encuentra el sender, elegir un bot al azar por si acaso
                            responding_bot = random.choice(self.active_bots)
                    else:
                        # Si es un humano, elegir un bot al azar
                        responding_bot = random.choice(self.active_bots)
                    log.info(f"Random reply triggered in channel by '{responding_bot.name}' (chance: {self.reply_chance*100}%).")
                else:
                    log.info("Ignoring message as it did not meet the conditions for a reply.")
                    return

            # Si el mensaje es de un chat privado, siempre responder con el primer bot
            if not should_reply and not is_channel_post:
                should_reply = True
                responding_bot = self.active_bots[0] # Usar el primer bot cargado por defecto

            if not should_reply or not text:
                log.info("Message did not require a response or was not text. Ignoring.")
                return

            log.info(f"Received message from Telegram: {text}")

            # Construir el prompt para Gemini con la personalidad del bot seleccionado
            language = self.config.get('BITWIT_LANGUAGE', 'es')
            language_instruction = "Responde en español." if language == 'es' else "Respond in English."
            
            prompt = (
                f"{responding_bot.personality_prompt}\n\n"
                f"Historial de la conversación:\n\n" # El historial está vacío temporalmente
                f"El siguiente mensaje proviene de un humano: '{cleaned_text}'\n"
                f"{language_instruction} Tu respuesta debe ser concisa, reflejar tu personalidad y responder al mensaje del humano."
            )
            
            gemini_response = self.gemini_client.generate_text_with_llm(responding_bot.name, prompt)
            log.info(f"Gemini responded with: {gemini_response}")

            # Obtener el token del bot que va a responder de la configuración
            token_key = f"TELEGRAM_{responding_bot.name.upper()}_TOKEN"
            telegram_token = self.config.get(token_key)
            if not telegram_token:
                log.error(f"Token no encontrado para el bot '{responding_bot.name}'. No se puede responder.")
                self.send_telegram_message(chat_id, "Lo siento, hubo un error de configuración y no puedo responder.")
                return

            # Verificar si la respuesta contiene una petición de imagen
            image_prompt_tag = "IMAGE PROMPT:"
            if image_prompt_tag in gemini_response:
                parts = gemini_response.split(image_prompt_tag)
                text_response = parts[0].strip()
                image_prompt = parts[1].strip()
                
                log.info(f"Image prompt detected. Prompt: {image_prompt}")
                image_path = self.gemini_client.generate_image_with_llm(image_prompt)
                
                if image_path:
                    log.info("Sending photo to Telegram.")
                    # Ahora pasamos el token correcto a la función de envío
                    self.send_telegram_photo(chat_id, image_path, text_response, bot_token=telegram_token)
                else:
                    log.info("Image generation was skipped. Sending text only.")
                    self.send_telegram_message(chat_id, text_response, bot_token=telegram_token)
                return  # <--- Salir después de procesar la imagen
            
            # Si no hay etiqueta de imagen, solo enviar el texto
            self.send_telegram_message(chat_id, gemini_response, bot_token=telegram_token)

        except Exception as e:
            log.error(f"Error handling Telegram message: {e}", exc_info=True)
            # En caso de error, responder con el token principal (BitWit)
            fallback_token = self.config.get("TELEGRAM_BITWIT_TOKEN")
            self.send_telegram_message(chat_id, "Lo siento, hubo un error al procesar tu solicitud.", bot_token=fallback_token)
        """
        Processes an incoming message from the Telegram webhook,
        differentiating between private chats and channel posts.
        """
        try:
            message = data.get('message')
            if not message:
                message = data.get('channel_post') or data.get('edited_channel_post')
                if not message:
                    log.warning("Received a Telegram update without a message or channel post object.")
                    return

            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            is_channel_post = message['chat']['type'] in ['channel', 'group', 'supergroup']
            is_from_bot = message['from'].get('is_bot', False)
            
            should_reply = False
            responding_bot = None
            cleaned_text = text
            
            # 1. Verificar si se ha mencionado a algún bot activo (directa o indirectamente)
            for bot in self.active_bots:
                # La lógica de nombre de usuario ahora usa el nombre del bot de la DB
                username_key = f"TELEGRAM_{bot.name.upper()}_USERNAME"
                bot_username = self.config.get(username_key, '').lower()
                bot_name_lower = bot.name.lower() # Nombre del bot en minúsculas

                # Si se le menciona directamente con @ o si se le menciona por su nombre
                if bot_username in text.lower() or f" {bot_name_lower}" in text.lower():
                    should_reply = True
                    # CORRECTO: El bot que responde es el que se ha mencionado
                    responding_bot = bot
                    
                    # Eliminar la mención para que no afecte el prompt
                    cleaned_text = text.lower().replace(bot_username, '').replace(f" {bot_name_lower}", '').strip()
                    log.info(f"Bot '{bot.name}' was mentioned directly or by name. Preparing to respond.")
                    break
            
            # 2. Si no se mencionó a nadie, usar la probabilidad para decidir si responder
            if not should_reply and is_channel_post:
                if random.random() < self.reply_chance:
                    should_reply = True
                    # Lógica para que el bot que no posteó el último mensaje responda
                    if is_from_bot:
                        sender_id = message['from']['id']
                        # Encontrar el bot que envió el mensaje
                        sender_bot = next((b for b in self.active_bots if b.telegram_id == str(sender_id)), None)
                        if sender_bot:
                            # Encontrar al otro bot
                            responding_bot = next((b for b in self.active_bots if b.name != sender_bot.name), None)
                        else:
                            # Si no se encuentra el sender, elegir un bot al azar por si acaso
                            responding_bot = random.choice(self.active_bots)
                    else:
                        # Si es un humano, elegir un bot al azar
                        responding_bot = random.choice(self.active_bots)
                    log.info(f"Random reply triggered in channel by '{responding_bot.name}' (chance: {self.reply_chance*100}%).")
                else:
                    log.info("Ignoring message as it did not meet the conditions for a reply.")
                    return

            # Si el mensaje es de un chat privado, siempre responder con el primer bot
            if not should_reply and not is_channel_post:
                should_reply = True
                responding_bot = self.active_bots[0] # Usar el primer bot cargado por defecto

            if not should_reply or not text:
                log.info("Message did not require a response or was not text. Ignoring.")
                return

            log.info(f"Received message from Telegram: {text}")

            # Construir el prompt para Gemini con la personalidad del bot seleccionado
            language = self.config.get('BITWIT_LANGUAGE', 'es')
            language_instruction = "Responde en español." if language == 'es' else "Respond in English."
            
            prompt = (
                f"{responding_bot.personality_prompt}\n\n"
                f"Historial de la conversación:\n\n" # El historial está vacío temporalmente
                f"El siguiente mensaje proviene de un humano: '{cleaned_text}'\n"
                f"{language_instruction} Tu respuesta debe ser concisa, reflejar tu personalidad y responder al mensaje del humano."
            )
            
            gemini_response = self.gemini_client.generate_text_with_llm(responding_bot.name, prompt)
            log.info(f"Gemini responded with: {gemini_response}")

            # Obtener el token del bot que va a responder de la configuración
            token_key = f"TELEGRAM_{responding_bot.name.upper()}_TOKEN"
            telegram_token = self.config.get(token_key)
            if not telegram_token:
                log.error(f"Token no encontrado para el bot '{responding_bot.name}'. No se puede responder.")
                self.send_telegram_message(chat_id, "Lo siento, hubo un error de configuración y no puedo responder.")
                return

            # Verificar si la respuesta contiene una petición de imagen
            image_prompt_tag = "IMAGE PROMPT:"
            if image_prompt_tag in gemini_response:
                parts = gemini_response.split(image_prompt_tag)
                text_response = parts[0].strip()
                image_prompt = parts[1].strip()
                
                log.info(f"Image prompt detected. Prompt: {image_prompt}")
                image_path = self.gemini_client.generate_image_with_llm(image_prompt)
                
                if image_path:
                    log.info("Sending photo to Telegram.")
                    # Ahora pasamos el token correcto a la función de envío
                    self.send_telegram_photo(chat_id, image_path, text_response, bot_token=telegram_token)
                else:
                    log.info("Image generation was skipped. Sending text only.")
                    self.send_telegram_message(chat_id, text_response, bot_token=telegram_token)
                return  # <--- Salir después de procesar la imagen
            
            # Si no hay etiqueta de imagen, solo enviar el texto
            self.send_telegram_message(chat_id, gemini_response, bot_token=telegram_token)

        except Exception as e:
            log.error(f"Error handling Telegram message: {e}", exc_info=True)
            # En caso de error, responder con el token principal (BitWit)
            fallback_token = self.config.get("TELEGRAM_BITWIT_TOKEN")
            self.send_telegram_message(chat_id, "Lo siento, hubo un error al procesar tu solicitud.", bot_token=fallback_token)
        """
        Processes an incoming message from the Telegram webhook,
        differentiating between private chats and channel posts.
        """
        try:
            message = data.get('message')
            if not message:
                message = data.get('channel_post') or data.get('edited_channel_post')
                if not message:
                    log.warning("Received a Telegram update without a message or channel post object.")
                    return

            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            is_channel_post = message['chat']['type'] in ['channel', 'group', 'supergroup']
            is_from_bot = message['from'].get('is_bot', False)
            
            should_reply = False
            responding_bot = None
            cleaned_text = text
            
            # 1. Verificar si se ha mencionado a algún bot activo (directa o indirectamente)
            for bot in self.active_bots:
                # La lógica de nombre de usuario ahora usa el nombre del bot de la DB
                username_key = f"TELEGRAM_{bot.name.upper()}_USERNAME"
                bot_username = self.config.get(username_key, '').lower()
                bot_name_lower = bot.name.lower() # Nombre del bot en minúsculas

                # Si se le menciona directamente con @ o si se le menciona por su nombre
                if bot_username in text.lower() or f" {bot_name_lower}" in text.lower():
                    should_reply = True
                    # La respuesta debe ser del bot mencionado, no del otro
                    responding_bot = bot
                    
                    # Eliminar la mención para que no afecte el prompt
                    cleaned_text = text.lower().replace(bot_username, '').replace(f" {bot_name_lower}", '').strip()
                    log.info(f"Bot '{bot.name}' was mentioned directly or by name. Preparing to respond.")
                    break
            
            # 2. Si no se mencionó a nadie, usar la probabilidad para decidir si responder
            if not should_reply and is_channel_post:
                if random.random() < self.reply_chance:
                    should_reply = True
                    # Lógica para que el bot que no posteó el último mensaje responda
                    if is_from_bot:
                        sender_id = message['from']['id']
                        # Encontrar el bot que envió el mensaje
                        sender_bot = next((b for b in self.active_bots if b.telegram_id == str(sender_id)), None)
                        if sender_bot:
                            # Encontrar al otro bot
                            responding_bot = next((b for b in self.active_bots if b.name != sender_bot.name), None)
                        else:
                            # Si no se encuentra el sender, elegir un bot al azar por si acaso
                            responding_bot = random.choice(self.active_bots)
                    else:
                        # Si es un humano, elegir un bot al azar
                        responding_bot = random.choice(self.active_bots)
                    log.info(f"Random reply triggered in channel by '{responding_bot.name}' (chance: {self.reply_chance*100}%).")
                else:
                    log.info("Ignoring message as it did not meet the conditions for a reply.")
                    return

            # Si el mensaje es de un chat privado, siempre responder con el primer bot
            if not should_reply and not is_channel_post:
                should_reply = True
                responding_bot = self.active_bots[0] # Usar el primer bot cargado por defecto

            if not should_reply or not text:
                log.info("Message did not require a response or was not text. Ignoring.")
                return

            log.info(f"Received message from Telegram: {text}")

            # Construir el prompt para Gemini con la personalidad del bot seleccionado
            language = self.config.get('BITWIT_LANGUAGE', 'es')
            language_instruction = "Responde en español." if language == 'es' else "Respond in English."
            
            prompt = (
                f"{responding_bot.personality_prompt}\n\n"
                f"Historial de la conversación:\n\n" # El historial está vacío temporalmente
                f"El siguiente mensaje proviene de un humano: '{cleaned_text}'\n"
                f"{language_instruction} Tu respuesta debe ser concisa, reflejar tu personalidad y responder al mensaje del humano."
            )
            
            gemini_response = self.gemini_client.generate_text_with_llm(responding_bot.name, prompt)
            log.info(f"Gemini responded with: {gemini_response}")

            # Obtener el token del bot que va a responder de la configuración
            token_key = f"TELEGRAM_{responding_bot.name.upper()}_TOKEN"
            telegram_token = self.config.get(token_key)
            if not telegram_token:
                log.error(f"Token no encontrado para el bot '{responding_bot.name}'. No se puede responder.")
                self.send_telegram_message(chat_id, "Lo siento, hubo un error de configuración y no puedo responder.")
                return

            # Verificar si la respuesta contiene una petición de imagen
            image_prompt_tag = "IMAGE PROMPT:"
            if image_prompt_tag in gemini_response:
                parts = gemini_response.split(image_prompt_tag)
                text_response = parts[0].strip()
                image_prompt = parts[1].strip()
                
                log.info(f"Image prompt detected. Prompt: {image_prompt}")
                image_path = self.gemini_client.generate_image_with_llm(image_prompt)
                
                if image_path:
                    log.info("Sending photo to Telegram.")
                    # Ahora pasamos el token correcto a la función de envío
                    self.send_telegram_photo(chat_id, image_path, text_response, bot_token=telegram_token)
                else:
                    log.info("Image generation was skipped. Sending text only.")
                    self.send_telegram_message(chat_id, text_response, bot_token=telegram_token)
                return  # <--- Salir después de procesar la imagen
            
            # Si no hay etiqueta de imagen, solo enviar el texto
            self.send_telegram_message(chat_id, gemini_response, bot_token=telegram_token)

        except Exception as e:
            log.error(f"Error handling Telegram message: {e}", exc_info=True)
            # En caso de error, responder con el token principal (BitWit)
            fallback_token = self.config.get("TELEGRAM_BITWIT_TOKEN")
            self.send_telegram_message(chat_id, "Lo siento, hubo un error al procesar tu solicitud.", bot_token=fallback_token)
        """
        Processes an incoming message from the Telegram webhook,
        differentiating between private chats and channel posts.
        """
        try:
            message = data.get('message')
            if not message:
                message = data.get('channel_post') or data.get('edited_channel_post')
                if not message:
                    log.warning("Received a Telegram update without a message or channel post object.")
                    return

            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            is_channel_post = message['chat']['type'] in ['channel', 'group', 'supergroup']
            is_from_bot = message['from'].get('is_bot', False)
            
            should_reply = False
            responding_bot = None
            cleaned_text = text
            
            # 1. Verificar si se ha mencionado a algún bot activo (directa o indirectamente)
            for bot in self.active_bots:
                # La lógica de nombre de usuario ahora usa el nombre del bot de la DB
                username_key = f"TELEGRAM_{bot.name.upper()}_USERNAME"
                bot_username = self.config.get(username_key, '').lower()
                bot_name_lower = bot.name.lower() # Nombre del bot en minúsculas

                # Si se le menciona directamente con @ o si se le menciona por su nombre
                if bot_username in text.lower() or f" {bot_name_lower}" in text.lower():
                    should_reply = True
                    # Si el bot mencionado ya respondió, buscar al otro bot para que responda
                    if bot.name == "Bitwit":
                        responding_bot = next((b for b in self.active_bots if b.name == "Veritas"), None)
                    else:
                        responding_bot = next((b for b in self.active_bots if b.name == "Bitwit"), None)
                    
                    # Eliminar la mención para que no afecte el prompt
                    cleaned_text = text.lower().replace(bot_username, '').replace(f" {bot_name_lower}", '').strip()
                    log.info(f"Bot '{bot.name}' was mentioned directly or by name. Preparing to respond.")
                    break
            
            # 2. Si no se mencionó a nadie, usar la probabilidad para decidir si responder
            if not should_reply and is_channel_post:
                if random.random() < self.reply_chance:
                    should_reply = True
                    # Lógica para que el bot que no posteó el último mensaje responda
                    if is_from_bot:
                        sender_id = message['from']['id']
                        # Encontrar el bot que envió el mensaje
                        sender_bot = next((b for b in self.active_bots if b.telegram_id == str(sender_id)), None)
                        if sender_bot:
                            # Encontrar al otro bot
                            responding_bot = next((b for b in self.active_bots if b.name != sender_bot.name), None)
                        else:
                            # Si no se encuentra el sender, elegir un bot al azar por si acaso
                            responding_bot = random.choice(self.active_bots)
                    else:
                        # Si es un humano, elegir un bot al azar
                        responding_bot = random.choice(self.active_bots)
                    log.info(f"Random reply triggered in channel by '{responding_bot.name}' (chance: {self.reply_chance*100}%).")
                else:
                    log.info("Ignoring message as it did not meet the conditions for a reply.")
                    return

            # Si el mensaje es de un chat privado, siempre responder con el primer bot
            if not should_reply and not is_channel_post:
                should_reply = True
                responding_bot = self.active_bots[0] # Usar el primer bot cargado por defecto

            if not should_reply or not text:
                log.info("Message did not require a response or was not text. Ignoring.")
                return

            log.info(f"Received message from Telegram: {text}")

            # Construir el prompt para Gemini con la personalidad del bot seleccionado
            language = self.config.get('BITWIT_LANGUAGE', 'es')
            language_instruction = "Responde en español." if language == 'es' else "Respond in English."
            
            prompt = (
                f"{responding_bot.personality_prompt}\n\n"
                f"Historial de la conversación:\n\n" # El historial está vacío temporalmente
                f"El siguiente mensaje proviene de un humano: '{cleaned_text}'\n"
                f"{language_instruction} Tu respuesta debe ser concisa, reflejar tu personalidad y responder al mensaje del humano."
            )
            
            gemini_response = self.gemini_client.generate_text_with_llm(responding_bot.name, prompt)
            log.info(f"Gemini responded with: {gemini_response}")

            # Obtener el token del bot que va a responder de la configuración
            token_key = f"TELEGRAM_{responding_bot.name.upper()}_TOKEN"
            telegram_token = self.config.get(token_key)
            if not telegram_token:
                log.error(f"Token no encontrado para el bot '{responding_bot.name}'. No se puede responder.")
                self.send_telegram_message(chat_id, "Lo siento, hubo un error de configuración y no puedo responder.")
                return

            # Verificar si la respuesta contiene una petición de imagen
            image_prompt_tag = "IMAGE PROMPT:"
            if image_prompt_tag in gemini_response:
                parts = gemini_response.split(image_prompt_tag)
                text_response = parts[0].strip()
                image_prompt = parts[1].strip()
                
                log.info(f"Image prompt detected. Prompt: {image_prompt}")
                image_path = self.gemini_client.generate_image_with_llm(image_prompt)
                
                if image_path:
                    log.info("Sending photo to Telegram.")
                    # Ahora pasamos el token correcto a la función de envío
                    self.send_telegram_photo(chat_id, image_path, text_response, bot_token=telegram_token)
                else:
                    log.info("Image generation was skipped. Sending text only.")
                    self.send_telegram_message(chat_id, text_response, bot_token=telegram_token)
                return  # <--- Salir después de procesar la imagen
            
            # Si no hay etiqueta de imagen, solo enviar el texto
            self.send_telegram_message(chat_id, gemini_response, bot_token=telegram_token)

        except Exception as e:
            log.error(f"Error handling Telegram message: {e}", exc_info=True)
            # En caso de error, responder con el token principal (BitWit)
            fallback_token = self.config.get("TELEGRAM_BITWIT_TOKEN")
            self.send_telegram_message(chat_id, "Lo siento, hubo un error al procesar tu solicitud.", bot_token=fallback_token)


    def send_telegram_message(self, chat_id, text, bot_token=None):
        """
        Sends a message back to Telegram using the provided bot token,
        or the default one if not specified.
        """
        token_to_use = bot_token if bot_token else self.config.get("TELEGRAM_BITWIT_TOKEN")
        if not token_to_use:
            log.error("Telegram bot token not found in configuration. Cannot send message.")
            return

        api_url = f"https://api.telegram.org/bot{token_to_use}/sendMessage"
        
        try:
            response = requests.post(api_url, json={
                "chat_id": chat_id,
                "text": text
            })
            response.raise_for_status()
            log.info(f"Telegram message sent successfully to chat ID {chat_id}.")
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to send Telegram message: {e}", exc_info=True)


    def send_telegram_photo(self, chat_id, photo_relative_path, caption, bot_token=None):
        """
        Sends a photo to Telegram using the provided bot token,
        or the default one if not specified.
        """
        token_to_use = bot_token if bot_token else self.config.get("TELEGRAM_BITWIT_TOKEN")
        if not token_to_use:
            log.error("Telegram bot token not found in configuration. Cannot send photo.")
            return

        api_url = f"https://api.telegram.org/bot{token_to_use}/sendPhoto"
        
        images_dir = self.config.get("GENERATED_IMAGES_DIR")
        if not images_dir:
            log.error("GENERATED_IMAGES_DIR not configured. Cannot send photo.")
            self.send_telegram_message(chat_id, "Lo siento, la ruta de la imagen no está configurada correctamente.")
            return
        
        image_filename = os.path.basename(photo_relative_path)
        full_photo_path = os.path.join(images_dir, image_filename)
        log.info(f"Attempting to open photo from full path: {full_photo_path}")

        try:
            with open(full_photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {'chat_id': chat_id, 'caption': caption}
                
                response = requests.post(api_url, data=data, files=files)
                response.raise_for_status()
                log.info(f"Telegram photo sent successfully to chat ID {chat_id}.")
        except FileNotFoundError:
            log.error(f"Photo file not found at: {full_photo_path}")
            self.send_telegram_message(chat_id, "Lo siento, no pude encontrar la imagen generada.")
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to send Telegram photo: {e}", exc_info=True)

