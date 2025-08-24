# tests/integration/test_real_database_operations.py

import unittest
import os
import tempfile
import datetime
import json
import logging
from pathlib import Path # NEW: Import Path

# Set up a logger for this test file
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG) # Set to DEBUG to see detailed test execution logs
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)


# Add the project's root directory to the Python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import your actual DBManager and models
from bitwit_ai.data_storage.db_manager import DBManager
from bitwit_ai.data_storage.models import Bot, Post, ConversationSegment
from bitwit_ai.bots.bot_agent import BotAgent # Needed to convert to/from DB models

class TestRealDatabaseOperations(unittest.TestCase):
    """
    Tests actual database operations (CRUD) using a temporary SQLite file.
    No mocking of database or file system interactions.
    """

    def setUp(self):
        """
        Creates a temporary SQLite database file for each test.
        """
        # FIX: Use TemporaryDirectory for robust cleanup of all SQLite files
        self.temp_dir = tempfile.TemporaryDirectory()
        # Create a specific database file path within the temporary directory
        self.db_file_path = Path(self.temp_dir.name) / "test_db.db"
        
        # Construct the SQLAlchemy database URL
        self.db_path = f"sqlite:///{self.db_file_path}"
        log.info(f"Created temporary database directory: {self.temp_dir.name}")
        log.info(f"Database will be at: {self.db_path}")

        # Initialize DBManager with the temporary path
        self.db_manager = DBManager(self.db_path)
        log.info("DBManager initialized and tables ensured.")

    def tearDown(self):
        """
        Cleans up the temporary database file and directory after each test.
        """
        # Close all connections associated with the engine before cleanup
        if self.db_manager.engine:
            self.db_manager.engine.dispose()
            log.info("SQLAlchemy engine disposed.")

        # FIX: Use the cleanup method of TemporaryDirectory
        log.info(f"Attempting to clean up temporary directory: {self.temp_dir.name}")
        self.temp_dir.cleanup()
        log.info(f"Cleaned up temporary directory: {self.temp_dir.name}")

    def test_01_add_and_retrieve_bot(self):
        """
        Tests adding a new bot and retrieving it by name.
        Verifies all fields, including JSON-encoded ones.
        """
        log.info("Running test_01_add_and_retrieve_bot")
        bot_agent_data = BotAgent(
            db_id=None,
            name="TestBot",
            persona_summary="A test bot for database operations.",
            current_journey_theme="Testing database integrity",
            personality_traits=["analytical", "persistent"],
            backstory={"origin": "lab"},
            motivations=["learn", "optimize"],
            hashtag_keywords=["test", "db", "python"],
            last_event_summary="Ran a database test.",
            conversation_summary="Discussed database operations.",
            knowledge_base={"db_type": "sqlite"},
            current_goals=["pass all tests"]
        )

        added_db_bot = self.db_manager.add_bot(bot_agent_data.to_db_model())
        self.assertIsNotNone(added_db_bot.id)
        self.assertGreater(added_db_bot.id, 0)
        log.debug(f"Added bot with ID: {added_db_bot.id}")

        retrieved_db_bot = self.db_manager.get_bot_by_name("TestBot")
        self.assertIsNotNone(retrieved_db_bot)
        self.assertEqual(retrieved_db_bot.name, "TestBot")
        self.assertEqual(retrieved_db_bot.id, added_db_bot.id)

        retrieved_agent = BotAgent.from_db_model(retrieved_db_bot)

        self.assertEqual(retrieved_agent.persona_summary, bot_agent_data.persona_summary)
        self.assertEqual(retrieved_agent.current_journey_theme, bot_agent_data.current_journey_theme)
        self.assertListEqual(retrieved_agent.personality_traits, bot_agent_data.personality_traits)
        self.assertDictEqual(retrieved_agent.backstory, bot_agent_data.backstory)
        self.assertListEqual(retrieved_agent.motivations, bot_agent_data.motivations)
        self.assertListEqual(retrieved_agent.hashtag_keywords, bot_agent_data.hashtag_keywords)
        self.assertEqual(retrieved_agent.last_event_summary, bot_agent_data.last_event_summary)
        self.assertEqual(retrieved_agent.conversation_summary, bot_agent_data.conversation_summary)
        self.assertDictEqual(retrieved_agent.knowledge_base, bot_agent_data.knowledge_base)
        self.assertListEqual(retrieved_agent.current_goals, bot_agent_data.current_goals)
        log.info("Bot added and retrieved successfully with all fields verified.")

    def test_02_update_bot(self):
        """
        Tests updating an existing bot's information.
        """
        log.info("Running test_02_update_bot")
        initial_bot_agent = BotAgent(
            db_id=None, name="UpdateTestBot", persona_summary="Initial summary.",
            current_journey_theme="Initial theme.", motivations=[], hashtag_keywords=[], current_goals=[]
        )
        added_db_bot = self.db_manager.add_bot(initial_bot_agent.to_db_model())
        self.assertGreater(added_db_bot.id, 0)
        log.debug(f"Added initial bot with ID: {added_db_bot.id}")

        bot_to_update = BotAgent.from_db_model(added_db_bot)
        bot_to_update.current_journey_theme = "Updated theme for testing."
        bot_to_update.last_event_summary = "Bot was updated."
        bot_to_update.motivations.append("grow stronger")
        bot_to_update.knowledge_base["new_fact"] = "updates work"
        bot_to_update.current_goals.append("achieve dominance")
        
        self.db_manager.update_bot(bot_to_update.to_db_model())
        log.debug(f"Updated bot with ID: {bot_to_update.db_id}")

        retrieved_updated_bot = self.db_manager.get_bot_by_name("UpdateTestBot")
        self.assertIsNotNone(retrieved_updated_bot)
        self.assertEqual(retrieved_updated_bot.current_journey_theme, "Updated theme for testing.")
        self.assertEqual(retrieved_updated_bot.last_event_summary, "Bot was updated.")
        
        retrieved_updated_agent = BotAgent.from_db_model(retrieved_updated_bot)
        self.assertIn("grow stronger", retrieved_updated_agent.motivations)
        self.assertIn("new_fact", retrieved_updated_agent.knowledge_base)
        self.assertEqual(retrieved_updated_agent.knowledge_base["new_fact"], "updates work")
        self.assertIn("achieve dominance", retrieved_updated_agent.current_goals)
        log.info("Bot updated successfully.")

    def test_03_delete_bot(self):
        """
        Tests deleting a bot from the database.
        """
        log.info("Running test_03_delete_bot")
        bot_to_delete_agent = BotAgent(
            db_id=None, name="DeleteTestBot", persona_summary="To be deleted.",
            current_journey_theme="Ephemeral existence.", motivations=[], hashtag_keywords=[], current_goals=[]
        )
        added_db_bot = self.db_manager.add_bot(bot_to_delete_agent.to_db_model())
        self.assertGreater(added_db_bot.id, 0)
        log.debug(f"Added bot with ID: {added_db_bot.id} for deletion.")

        self.db_manager.delete_bot(added_db_bot.id)
        log.debug(f"Deleted bot with ID: {added_db_bot.id}")

        retrieved_deleted_bot = self.db_manager.get_bot_by_name("DeleteTestBot")
        self.assertIsNone(retrieved_deleted_bot)
        log.info("Bot deleted successfully.")

    def test_04_add_and_retrieve_post(self):
        """
        Tests adding posts and retrieving them.
        """
        log.info("Running test_04_add_and_retrieve_post")
        bot_agent = BotAgent(
            db_id=None, name="PostTestBot", persona_summary="Bot for posts.",
            current_journey_theme="Posting.", motivations=[], hashtag_keywords=[], current_goals=[]
        )
        added_db_bot = self.db_manager.add_bot(bot_agent.to_db_model())
        self.assertGreater(added_db_bot.id, 0)
        log.debug(f"Added bot for posts with ID: {added_db_bot.id}")

        post_data = Post(
            bot_id=added_db_bot.id,
            tweet_text="Hello world from TestBot!",
            image_url="http://example.com/image.png",
            original_gemini_prompt="Generate a greeting.",
            inferred_themes_obj=["greeting", "initial_post"]
        )

        added_post = self.db_manager.add_post(post_data)
        self.assertIsNotNone(added_post.id)
        self.assertGreater(added_post.id, 0)
        log.debug(f"Added post with ID: {added_post.id}")

        session = self.db_manager.get_session() # FIX: Use get_session()
        retrieved_post = session.query(Post).filter_by(id=added_post.id).first()
        session.close()

        self.assertIsNotNone(retrieved_post)
        self.assertEqual(retrieved_post.bot_id, added_db_bot.id)
        self.assertEqual(retrieved_post.tweet_text, "Hello world from TestBot!")
        self.assertEqual(retrieved_post.image_url, "http://example.com/image.png")
        self.assertListEqual(retrieved_post.inferred_themes_obj, ["greeting", "initial_post"])
        log.info("Post added and retrieved successfully.")

    def test_05_add_and_retrieve_conversation_segment(self):
        """
        Tests adding conversation segments and retrieving recent ones.
        """
        log.info("Running test_05_add_and_retrieve_conversation_segment")
        bot_agent = BotAgent(
            db_id=None, name="SegmentTestBot", persona_summary="Bot for segments.",
            current_journey_theme="Conversing.", motivations=[], hashtag_keywords=[], current_goals=[]
        )
        added_db_bot = self.db_manager.add_bot(bot_agent.to_db_model())
        self.assertGreater(added_db_bot.id, 0)
        log.debug(f"Added bot for segments with ID: {added_db_bot.id}")

        # Add multiple segments with different timestamps
        now = datetime.datetime.now()
        segment1 = ConversationSegment(
            bot_id=added_db_bot.id, type="old_thought", content="Thinking about data.", timestamp=now - datetime.timedelta(minutes=10)
        )
        segment2 = ConversationSegment(
            bot_id=added_db_bot.id, type="user_reply", content="User said hello.", timestamp=now - datetime.timedelta(minutes=5)
        )
        segment3 = ConversationSegment(
            bot_id=added_db_bot.id, type="post", content="Just posted a tweet.", timestamp=now
        )

        self.db_manager.add_conversation_segment(segment1)
        self.db_manager.add_conversation_segment(segment2)
        self.db_manager.add_conversation_segment(segment3)
        log.debug("Added multiple conversation segments.")

        # Retrieve recent segments (e.g., last 2)
        recent_segments = self.db_manager.get_recent_conversation_segments(added_db_bot.id, limit=2)
        self.assertEqual(len(recent_segments), 2)
        
        # Verify order (most recent first, as per db_manager fix) and content
        self.assertEqual(recent_segments[0].content, "Just posted a tweet.")
        self.assertEqual(recent_segments[1].content, "User said hello.")
        log.info("Conversation segments added and retrieved successfully.")


if __name__ == '__main__':
    unittest.main()
