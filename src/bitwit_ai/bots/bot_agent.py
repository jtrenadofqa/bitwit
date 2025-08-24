# src/bitwit_ai/bots/bot_agent.py

from dataclasses import dataclass, field
import datetime
from typing import List, Dict, Any, Optional
import json
import logging
import re
from bitwit_ai.config_manager import ConfigManager

from bitwit_ai.data_storage.models import Bot # Ensure Bot is imported

log = logging.getLogger(__name__)

@dataclass
class BotAgent:
    """
    Represents an active AI bot instance, holding its personality, state,
    and methods to interact with its memory.
    """
    # --- REQUIRED FIELDS (NO DEFAULTS) ---
    db_id: int
    name: str
    persona_summary: str # This is your core system prompt guidance stored in DB
    current_journey_theme: str
    current_mood: str # NEW: Required field for the bot's current emotional state

    # --- OPTIONAL FIELDS (WITH DEFAULTS) ---
    personality_traits: List[str] = field(default_factory=list)
    backstory: Dict[str, Any] = field(default_factory=dict)
    motivations: List[str] = field(default_factory=list)
    hashtag_keywords: List[str] = field(default_factory=list)
    allowed_moods: List[str] = field(default_factory=list) # NEW: List of moods this bot can express

    # Current Journey & State (dynamic, updated in real-time)
    last_event_summary: Optional[str] = None
    conversation_summary: Optional[str] = None # This will now be dynamically updated by AI
    knowledge_base: Dict[str, Any] = field(default_factory=dict) # Key facts/learnings
    current_goals: List[str] = field(default_factory=list) # Changed to List[str] as per template

    # Operational Details (mostly from DB or current session)
    twitter_account_id: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    is_active: bool = True
    last_posted_at: Optional[datetime.datetime] = None

    # Runtime-only memory: Not stored in DB, populated dynamically by ContentPipeline
    recent_conversation_history: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.config_manager = ConfigManager()
        self.language = self.config_manager.get('LANGUAGE', 'en')
        log.info(f"Bot '{self.name}' initialized with language '{self.language}'")

    @classmethod
    def from_db_model(cls, db_bot: Bot):
        """Creates a BotAgent instance from a SQLAlchemy Bot model object."""
        return cls(
            db_id=db_bot.id,
            name=db_bot.name,
            persona_summary=db_bot.persona_summary,
            current_journey_theme=db_bot.current_journey_theme,
            current_mood=db_bot.current_mood, # NEW: Load current_mood from DB
            personality_traits=db_bot.personality_traits_obj or [],
            backstory=db_bot.backstory_obj or {},
            motivations=db_bot.motivations_obj or [],
            hashtag_keywords=db_bot.hashtag_keywords_obj or [],
            allowed_moods=db_bot.allowed_moods_obj or [], # NEW: Load allowed_moods from DB
            last_event_summary=db_bot.last_event_summary,
            conversation_summary=db_bot.conversation_summary,
            knowledge_base=db_bot.knowledge_base_obj or {},
            current_goals=db_bot.current_goals_obj or [],
            twitter_account_id=db_bot.twitter_account_id,
            twitter_access_token=db_bot.twitter_access_token,
            twitter_access_token_secret=db_bot.twitter_access_token_secret,
            telegram_chat_id=db_bot.telegram_chat_id,
            is_active=db_bot.is_active,
            last_posted_at=db_bot.last_posted_at,
        )

    def to_db_model(self, db_bot_model=None):
        """
        Converts the BotAgent instance back to a SQLAlchemy Bot model object
        for saving updates to the database.
        """
        if db_bot_model is None:
            db_bot_model = Bot()
            if self.db_id is not None and self.db_id != 0:
                db_bot_model.id = self.db_id

        db_bot_model.name = self.name
        db_bot_model.persona_summary = self.persona_summary
        db_bot_model.personality_traits_obj = self.personality_traits
        db_bot_model.backstory_obj = self.backstory
        db_bot_model.motivations_obj = self.motivations
        db_bot_model.hashtag_keywords_obj = self.hashtag_keywords
        db_bot_model.current_journey_theme = self.current_journey_theme
        db_bot_model.current_mood = self.current_mood # NEW: Save current_mood to DB
        db_bot_model.allowed_moods_obj = self.allowed_moods # NEW: Save allowed_moods to DB
        db_bot_model.last_event_summary = self.last_event_summary
        db_bot_model.conversation_summary = self.conversation_summary
        db_bot_model.knowledge_base_obj = self.knowledge_base
        db_bot_model.current_goals_obj = self.current_goals
        db_bot_model.twitter_account_id = self.twitter_account_id
        db_bot_model.twitter_access_token = self.twitter_access_token
        db_bot_model.twitter_access_token_secret = self.twitter_access_token_secret
        db_bot_model.telegram_chat_id = self.telegram_chat_id
        db_bot_model.is_active = self.is_active
        db_bot_model.last_posted_at = self.last_posted_at
        return db_bot_model

    @classmethod
    def from_personality_markdown(cls, markdown_content: str) -> 'BotAgent':
        """
        Parses markdown content from a personality file to create a BotAgent instance.
        """
        def extract_section(md_content, start_heading, end_heading=None):
            """Helper to extract content between two markdown headings, more robustly."""
            escaped_start = re.escape(start_heading)
            
            if end_heading:
                escaped_end = re.escape(end_heading)
                pattern = rf"##\s*{escaped_start}.*?\n(.*?)(?=\n##\s*{escaped_end}.*?|\Z)"
            else:
                pattern = rf"##\s*{escaped_start}.*?\n(.*)"

            match = re.search(pattern, md_content, re.DOTALL | re.IGNORECASE)
            content = match.group(1).strip() if match else ""
            
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1].strip()
            return content

        def parse_list_config(section_content, key_prefix):
            items = []
            # Updated regex to correctly capture multi-line lists under a prefix
            block_match = re.search(rf'^- {re.escape(key_prefix)}:\s*$(.*?)(?=\n^- |\Z)', section_content, re.DOTALL | re.MULTILINE)
            if block_match:
                items = [line.strip().lstrip('- ').strip() for line in block_match.group(1).split('\n') if line.strip()]
            return items

        def parse_simple_config_line(section_content, key):
            match = re.search(rf'^- {re.escape(key)}:\s*(.*)$', section_content, re.MULTILINE)
            return match.group(1).strip() if match else None

        # --- Parse Bot Configuration Section ---
        bot_config_section = extract_section(markdown_content, "Bot Configuration", "Key Personality Traits")
        
        parsed_name = parse_simple_config_line(bot_config_section, "Name")
        parsed_theme = parse_simple_config_line(bot_config_section, "Current Journey Theme")
        parsed_goals = parse_list_config(bot_config_section, "Goals:")
        parsed_motivations = parse_list_config(bot_config_section, "Motivations:")
        
        parsed_hashtag_keywords_str = parse_simple_config_line(bot_config_section, "Hashtag Keywords")
        parsed_hashtag_keywords = [k.strip() for k in parsed_hashtag_keywords_str.split(',') if k.strip()] if parsed_hashtag_keywords_str else []

        # --- Extract Initial System Prompt Guidance ---
        persona_summary_content = extract_section(markdown_content, "Initial System Prompt Guidance")
        
        # --- Extract Personality Traits ---
        personality_traits_section = extract_section(markdown_content, "Key Personality Traits", "Backstory")
        traits_list = re.findall(r'- \*\*(.*?)\*\*', personality_traits_section)
        parsed_personality_traits = [trait.strip() for trait in traits_list]

        # --- Extract Backstory ---
        backstory_section = extract_section(markdown_content, "Backstory", "Initial State")
        parsed_backstory = {"raw_content": backstory_section}

        # --- Extract Initial State (MODIFIED to include mood fields) ---
        initial_state_section = extract_section(markdown_content, "Initial State", "Initial System Prompt Guidance")
        
        parsed_initial_mood = parse_simple_config_line(initial_state_section, "Initial Mood")
        # NEW: Parse Allowed Emotional Modifiers
        parsed_allowed_moods_str = parse_simple_config_line(initial_state_section, "Allowed Emotional Modifiers")
        parsed_allowed_moods = [m.strip() for m in parsed_allowed_moods_str.split(',') if m.strip()] if parsed_allowed_moods_str else []

        # Fallback for initial mood if not specified or invalid
        if not parsed_initial_mood or parsed_initial_mood not in parsed_allowed_moods:
            parsed_initial_mood = parsed_allowed_moods[0] if parsed_allowed_moods else "Curious" # Default to first allowed or "Curious"
            log.warning(f"Initial Mood not specified or invalid for bot '{parsed_name}'. Defaulting to '{parsed_initial_mood}'.")


        last_event_summary_match = re.search(r'^- Last Event Summary:\s*(.*)$', initial_state_section, re.MULTILINE)
        parsed_last_event_summary = last_event_summary_match.group(1).strip() if last_event_summary_match else None

        conversation_summary_match = re.search(r'^- Conversation Summary:\s*(.*)$', initial_state_section, re.MULTILINE)
        parsed_conversation_summary = conversation_summary_match.group(1).strip() if conversation_summary_match else None

        knowledge_base_items_match = re.search(r'^- Knowledge Base \(Key Learnings\):\s*$(.*?)(?=\n- |\Z)', initial_state_section, re.DOTALL | re.MULTILINE)
        parsed_knowledge_base = {}
        if knowledge_base_items_match:
            for item_line in knowledge_base_items_match.group(1).split('\n'):
                item_line = item_line.strip().lstrip('- ').strip()
                if item_line:
                    if ':' in item_line:
                        key, value = item_line.split(':', 1)
                        parsed_knowledge_base[key.strip()] = value.strip()
                    else:
                        parsed_knowledge_base[f"learning_{len(parsed_knowledge_base) + 1}"] = item_line


        # --- Construct BotAgent instance ---
        return cls(
            db_id=0, # Placeholder, DBManager will assign real ID upon add_bot
            name=parsed_name if parsed_name else "DefaultBot",
            persona_summary=persona_summary_content, # This now includes the full system prompt guidance
            current_journey_theme=parsed_theme if parsed_theme else "general exploration",
            current_mood=parsed_initial_mood, # NEW: Initialize with parsed mood
            personality_traits=parsed_personality_traits,
            backstory=parsed_backstory,
            motivations=parsed_motivations,
            hashtag_keywords=parsed_hashtag_keywords,
            allowed_moods=parsed_allowed_moods, # NEW: Initialize with parsed allowed moods
            last_event_summary=parsed_last_event_summary,
            conversation_summary=parsed_conversation_summary,
            knowledge_base=parsed_knowledge_base,
            current_goals=parsed_goals,
        )

    def get_system_prompt_base(self) -> str:
        """
        Generates the foundational system prompt based on the bot's core identity.
        This is the primary way the AI's core persona is communicated to the LLM.
        """
        if self.language == 'es':
            language_instruction = "Responde siempre en español."
        elif self.language == 'en':
            language_instruction = "Always respond in English."
        else:
            language_instruction = ""
            log.warning(f"Unsupported language code '{self.language}' defined. Skipping language instruction.")

        system_prompt = self.persona_summary
        
        if self.motivations:
            system_prompt += "\n\nKey motivations driving your actions:"
            for i, motivation in enumerate(self.motivations):
                system_prompt += f"\n{i+1}. {motivation}"
        
        # NEW: Include current mood in the system prompt
        system_prompt += f"\n\nYour current intellectual state/mood is: {self.current_mood}. Let this subtly influence your tone and perspective."

        return f"{language_instruction}\n\n{system_prompt}"

    def get_current_state_prompt(self) -> str:
        """
        Generates the dynamic part of the prompt based on the bot's current state.
        This provides the AI with recent context and ongoing goals.
        """
        state_context = []
        if self.current_journey_theme:
            state_context.append(f"Current research theme: '{self.current_journey_theme}'.")
        
        if self.current_goals:
            goals_str = "; ".join(self.current_goals)
            state_context.append(f"Your current goals are: {goals_str}.")
        
        if self.last_event_summary:
            state_context.append(f"Recent analysis focus: '{self.last_event_summary}'.")
        if self.conversation_summary:
             state_context.append(f"Recent conversational context: '{self.conversation_summary}'.")
        if self.knowledge_base:
            kb_str = ", ".join([f"{k}: {v}" for k, v in self.knowledge_base.items()])
            state_context.append(f"Relevant knowledge: {kb_str}.")
        
        return "Context for tweet generation: " + " ".join(state_context) if state_context else ""

    def get_full_gemini_prompt(self) -> str:
        """
        Constructs the complete prompt to be sent to Gemini for content generation.
        Combines persona, current state, and relevant knowledge.
        """
        # Start with the core persona guidance and motivations
        prompt_parts = [self.get_system_prompt_base()]

        # Add context from the bot's current state and goals
        current_state_prompt = self.get_current_state_prompt()
        if current_state_prompt:
            prompt_parts.append(current_state_prompt)

        return "\n\n".join(prompt_parts).strip()

    def update_mood(self, new_mood_suggestion: str):
        """
        Updates the bot's current mood, validating against allowed moods.
        :param new_mood_suggestion: The mood suggested by the LLM based on analysis.
        """
        if new_mood_suggestion in self.allowed_moods:
            self.current_mood = new_mood_suggestion
            log.info(f"Bot '{self.name}' mood updated to: {self.current_mood}")
        else:
            log.warning(f"Invalid mood '{new_mood_suggestion}' suggested for bot '{self.name}'. "
                        f"Allowed moods are: {', '.join(self.allowed_moods)}. Mood remains '{self.current_mood}'.")
            # Optionally, revert to a default neutral mood if the suggested mood is invalid
            # For now, we'll just keep the old mood.
