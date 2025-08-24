# src/bitwit_ai/data_storage/models.py

# Removed the problematic self-import: from .models import Base, Bot, Post, ConversationSegment
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON # Import JSON for SQLite
import datetime
import json

Base = declarative_base()

# Custom type for JSON handling
# This is a simple approach, for complex JSON structures consider
# sqlalchemy.types.TypeDecorator or a dedicated JSON type if your DB supports it.
# For SQLite, JSON is text, so we'll just ensure it's loaded/dumped as JSON.
class JSONEncodedDict(Text):
    """Represents a JSON-encoded dictionary."""
    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value

class Bot(Base):
    __tablename__ = 'bots'
    id = Column(Integer, primary_key=True, autoincrement=True) # Ensure autoincrement=True
    name = Column(String, unique=True, nullable=False)
    persona_summary = Column(Text, nullable=False)
    # ADDED: personality_prompt column
    personality_prompt = Column(Text, nullable=False)
    personality_traits = Column(JSON, default='[]') # Stored as JSON string
    backstory = Column(JSON, default='{}') # Stored as JSON string
    motivations = Column(JSON, default='[]') # Stored as JSON string
    hashtag_keywords = Column(JSON, default='[]') # Stored as JSON string
    current_journey_theme = Column(String, nullable=False)
    last_event_summary = Column(Text)
    conversation_summary = Column(Text)
    knowledge_base = Column(JSON, default='{}') # Stored as JSON string
    current_goals = Column(JSON, default='[]') # Stored as JSON string

    # Mood-related fields
    current_mood = Column(String, default="Curious") # The bot's current intellectual/emotional state
    allowed_moods = Column(JSON, default='[]') # List of moods this bot is allowed to experience, stored as JSON string

    # Fields for topic management
    current_topic = Column(String, nullable=True) # The bot's current active topic
    topic_iteration_count = Column(Integer, default=0, nullable=False) # How many consecutive posts on this topic

    twitter_account_id = Column(String)
    twitter_access_token = Column(String)
    twitter_access_token_secret = Column(String)
    telegram_chat_id = Column(String)
    is_active = Column(Boolean, default=True)
    last_posted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # Relationships
    posts = relationship("Post", back_populates="bot", cascade="all, delete-orphan")
    conversation_segments = relationship("ConversationSegment", back_populates="bot", cascade="all, delete-orphan")

    def __repr__(self):
        # MODIFIED: Include current_mood, current_topic, and topic_iteration_count in __repr__
        return f"<Bot(id={self.id}, name='{self.name}', mood='{self.current_mood}', topic='{self.current_topic}', iter={self.topic_iteration_count})>"

    # Properties to handle JSON deserialization when accessing attributes
    @property
    def personality_traits_obj(self):
        return json.loads(self.personality_traits) if isinstance(self.personality_traits, str) else self.personality_traits

    @personality_traits_obj.setter
    def personality_traits_obj(self, value):
        self.personality_traits = json.dumps(value)

    @property
    def backstory_obj(self):
        return json.loads(self.backstory) if isinstance(self.backstory, str) else self.backstory

    @backstory_obj.setter
    def backstory_obj(self, value):
        self.backstory = json.dumps(value)

    @property
    def motivations_obj(self):
        return json.loads(self.motivations) if isinstance(self.motivations, str) else self.motivations

    @motivations_obj.setter
    def motivations_obj(self, value):
        self.motivations = json.dumps(value)

    @property
    def hashtag_keywords_obj(self):
        return json.loads(self.hashtag_keywords) if isinstance(self.hashtag_keywords, str) else self.hashtag_keywords

    @hashtag_keywords_obj.setter
    def hashtag_keywords_obj(self, value):
        self.hashtag_keywords = json.dumps(value)

    @property
    def knowledge_base_obj(self):
        return json.loads(self.knowledge_base) if isinstance(self.knowledge_base, str) else self.knowledge_base

    @knowledge_base_obj.setter
    def knowledge_base_obj(self, value):
        self.knowledge_base = json.dumps(value)

    @property
    def current_goals_obj(self):
        return json.loads(self.current_goals) if isinstance(self.current_goals, str) else self.current_goals

    @current_goals_obj.setter
    def current_goals_obj(self, value):
        self.current_goals = json.dumps(value)

    # Property for allowed_moods
    @property
    def allowed_moods_obj(self):
        return json.loads(self.allowed_moods) if isinstance(self.allowed_moods, str) else self.allowed_moods

    @allowed_moods_obj.setter
    def allowed_moods_obj(self, value):
        self.allowed_moods = json.dumps(value)


class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(Integer, ForeignKey('bots.id'), nullable=False)
    tweet_text = Column(Text, nullable=False)
    image_url = Column(String)
    original_gemini_prompt = Column(Text)
    inferred_themes = Column(JSON, default='[]') # Stored as JSON string
    created_at = Column(DateTime, default=datetime.datetime.now)
    # Fields for replies
    in_reply_to_tweet_id = Column(Integer, nullable=True)
    in_reply_to_author_name = Column(String, nullable=True)


    bot = relationship("Bot", back_populates="posts")

    def __repr__(self):
        return f"<Post(id={self.id}, bot_id={self.bot_id}, created_at='{self.created_at}')>"

    @property
    def inferred_themes_obj(self):
        return json.loads(self.inferred_themes) if isinstance(self.inferred_themes, str) else self.inferred_themes

    @inferred_themes_obj.setter
    def inferred_themes_obj(self, value):
        self.inferred_themes = json.dumps(value)


class ConversationSegment(Base):
    __tablename__ = 'conversation_segments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(Integer, ForeignKey('bots.id'), nullable=False)
    type = Column(String, nullable=False) # e.g., 'user_reply', 'bot_thought', 'post'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    # Field to store JSON metadata for segments (e.g., for replies)
    metadata_json = Column(Text, nullable=True)

    bot = relationship("Bot", back_populates="conversation_segments")

    def __repr__(self):
        return f"<ConversationSegment(id={self.id}, bot_id={self.bot_id}, type='{self.type}', timestamp='{self.timestamp}')>"

