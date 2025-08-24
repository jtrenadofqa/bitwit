# src/bitwit_ai/data_storage/db_manager.py

import logging
import datetime
import json
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload # Asegúrate de que joinedload esté importado
from sqlalchemy.exc import SQLAlchemyError
from .models import Base, Bot, Post, ConversationSegment

log = logging.getLogger(__name__)

class DBManager:
    def __init__(self, db_url: str, enable_read: bool = True, enable_write: bool = True):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        # Asegura que todas las tablas sean creadas. Esto creará nuevas columnas si models.py ha cambiado.
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.enable_read = enable_read
        self.enable_write = enable_write
        log.info(f"Database manager initialized for {db_url}. Read enabled: {enable_read}, Write enabled: {enable_write}.")
        log.debug(f"DEBUG: DBManager __init__ called. self.enable_read: {self.enable_read}, self.enable_write: {self.enable_write}")
        log.debug(f"DEBUG: DBManager instance ID: {id(self)}")


    def _get_session(self):
        return self.Session()

    def add_bot(self, bot_model: Bot) -> Bot:
        """Añade un nuevo bot a la base de datos."""
        if not self.enable_write:
            log.warning("Database write is disabled. Cannot add bot.")
            return bot_model
        
        session = self._get_session()
        try:
            session.add(bot_model)
            session.commit()
            session.refresh(bot_model) # Refresca para obtener cualquier ID autogenerado
            log.info(f"Bot '{bot_model.name}' added with ID: {bot_model.id}.")
            return bot_model
        except SQLAlchemyError as e:
            session.rollback()
            log.error(f"Error adding bot '{bot_model.name}': {e}")
            raise
        finally:
            session.close()

    def get_bot(self, bot_id: Optional[int] = None, bot_name: Optional[str] = None) -> Optional[Bot]:
        """Recupera un bot por ID o nombre."""
        if not self.enable_read:
            log.warning("Database read is disabled. Cannot retrieve bot.")
            return None
        
        session = self._get_session()
        try:
            query = session.query(Bot)
            if bot_id:
                bot = query.filter_by(id=bot_id).first()
                log.debug(f"Retrieved bot by ID {bot_id}: {bot.name if bot else 'None'}")
            elif bot_name:
                bot = query.filter_by(name=bot_name).first()
                log.debug(f"Retrieved bot by Name '{bot_name}': {bot.name if bot else 'None'}")
            else:
                log.warning("get_bot called without bot_id or bot_name.")
                return None
            return bot
        except SQLAlchemyError as e:
            log.error(f"Error retrieving bot (ID: {bot_id}, Name: {bot_name}): {e}")
            raise
        finally:
            session.close()

    def get_all_bots(self) -> List[Bot]:
        """Recupera todos los bots de la base de datos."""
        if not self.enable_read:
            log.warning("Database read is disabled. Cannot retrieve all bots.")
            return []
        
        session = self._get_session()
        try:
            bots = session.query(Bot).all()
            log.debug(f"Retrieved {len(bots)} bots from DB.")
            return bots
        except SQLAlchemyError as e:
            log.error(f"Error retrieving all bots: {e}")
            raise
        finally:
            session.close()

    def update_bot(self, bot_model: Bot) -> Bot: # Cambiado el tipo de retorno a Bot para consistencia
        """Actualiza un bot existente en la base de datos."""
        if not self.enable_write:
            log.warning("Database write is disabled. Cannot update bot.")
            return bot_model # Retorna el modelo original si la escritura está deshabilitada
        
        session = self._get_session()
        try:
            # Fusiona el objeto bot_model desvinculado en la sesión actual
            bot_model = session.merge(bot_model)
            session.commit()
            session.refresh(bot_model) # Refresca el objeto después de la fusión y commit
            log.info(f"Bot '{bot_model.name}' (ID: {bot_model.id}) updated.")
            return bot_model # Retorna el modelo fusionado/actualizado
        except SQLAlchemyError as e:
            session.rollback()
            log.error(f"Error updating bot '{bot_model.name}' (ID: {bot_model.id}): {e}")
            raise
        finally:
            session.close()

    def delete_bot(self, bot_id: int):
        """Elimina un bot y sus posts y segmentos de conversación asociados."""
        if not self.enable_write:
            log.warning("Database write is disabled. Cannot delete bot.")
            return
        
        session = self._get_session()
        try:
            bot = session.query(Bot).filter_by(id=bot_id).first()
            if bot:
                session.delete(bot)
                session.commit()
                log.info(f"Bot '{bot.name}' (ID: {bot_id}) and its associated data deleted.")
            else:
                log.warning(f"Bot with ID {bot_id} not found for deletion.")
        except SQLAlchemyError as e:
            session.rollback()
            log.error(f"Error deleting bot with ID {bot_id}: {e}")
            raise
        finally:
            session.close()

    def add_post(self, post_model: Post) -> Post:
        """Añade un nuevo post (tweet) a la base de datos y lo devuelve con su bot cargado ansiosamente."""
        if not self.enable_write:
            log.warning("Database write is disabled. Cannot add post.")
            return post_model
        
        session = self._get_session()
        try:
            session.add(post_model)
            session.commit()
            session.refresh(post_model) # Refresca para obtener cualquier ID autogenerado y asegurar que está en la sesión

            # Carga ansiosamente la relación 'bot' para el post recién añadido
            # Esto asegura que 'post_model.bot' sea accesible después de que la sesión se cierre
            loaded_post = session.query(Post).options(joinedload(Post.bot)).filter_by(id=post_model.id).first()
            if loaded_post:
                log.info(f"Post added for bot ID {post_model.bot_id} with ID: {post_model.id}. Bot relationship eagerly loaded.")
                return loaded_post
            else:
                log.warning(f"Could not retrieve post with eagerly loaded bot after adding. Returning original post.")
                return post_model
        except SQLAlchemyError as e:
            session.rollback()
            log.error(f"Error adding post for bot ID {post_model.bot_id}: {e}")
            raise
        finally:
            session.close()

    def get_all_posts_with_bot_names(self) -> List[Post]:
        """
        Recupera todos los posts de la base de datos, cargando ansiosamente el nombre del bot asociado.
        """
        log.debug(f"DEBUG: get_all_posts_with_bot_names called. self.enable_read: {self.enable_read}")
        if not self.enable_read:
            log.warning("Database read is disabled. Cannot retrieve posts.")
            return []
        
        session = self._get_session()
        try:
            # Usa joinedload para obtener la relación del bot en la misma consulta
            posts = session.query(Post).options(joinedload(Post.bot)).order_by(Post.created_at).all() # Ordena por timestamp
            log.debug(f"Retrieved {len(posts)} posts from DB.")
            return posts
        except SQLAlchemyError as e:
            log.error(f"Error retrieving all posts: {e}")
            raise
        finally:
            session.close()

    def add_conversation_segment(self, segment_model: ConversationSegment) -> ConversationSegment:
        """Añade un nuevo segmento de conversación a la base de datos."""
        if not self.enable_write:
            log.warning("Database write is disabled. Cannot add conversation segment.")
            return segment_model
        
        session = self._get_session()
        try:
            session.add(segment_model)
            session.commit()
            log.info(f"Conversation segment added for bot ID {segment_model.bot_id} (Type: {segment_model.type}).")
            return segment_model
        except SQLAlchemyError as e:
            session.rollback()
            log.error(f"Error adding conversation segment for bot ID {segment_model.bot_id}: {e}")
            raise
        finally:
            session.close()

    def get_conversation_segments_for_bot(self, bot_id: int) -> List[ConversationSegment]:
        """Recupera todos los segmentos de conversación para un bot específico, ordenados por marca de tiempo."""
        if not self.enable_read:
            log.warning("Database read is disabled. Cannot retrieve conversation segments.")
            return []
        
        session = self._get_session()
        try:
            segments = session.query(ConversationSegment).filter_by(bot_id=bot_id).order_by(ConversationSegment.timestamp).all()
            log.debug(f"Retrieved {len(segments)} conversation segments for bot ID {bot_id}.")
            return segments
        except SQLAlchemyError as e:
            log.error(f"Error retrieving conversation segments for bot ID {bot_id}: {e}")
            raise
        finally:
            session.close()

    def dispose(self):
        """
        Libera el motor de SQLAlchemy, cerrando todas las conexiones en su pool de conexiones.
        Esto es crucial para asegurar un estado limpio de la base de datos, especialmente después de la eliminación de archivos.
        """
        if self.engine:
            log.info("Disposing of SQLAlchemy engine connections.")
            self.engine.dispose()
