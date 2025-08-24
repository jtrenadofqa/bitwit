# src/bots/message_formatter.py

import re
import logging
from typing import Any, Optional, Tuple, Union, List

log = logging.getLogger(__name__)

PatternTuple = Tuple[str, str, Union[int, None]]

class ContentPipeline:
    def __init__(self, platform_configs: dict):
        """
        Initializes the formatter with platform-specific rules (e.g., character limits).
        platform_configs might come from config_manager.
        Example: {'twitter_premium': True, 'twitter_char_limit': 25000}
        """
        self.platform_configs = platform_configs
        self.markdown_patterns: List[PatternTuple] = [
            (r'\*\*(.*?)\*\*', r'\1'),             # **bold**
            (r'\*(.*?)\*', r'\1'),                 # *italic*
            (r'__(.*?)__', r'\1'),                 # __underline__
            (r'_([^_]+)_', r'\1'),                 # _italic_
            (r'\[(.*?)\]\((.*?)\)', r'\1'),        # [link text](url) -> link text
            (r'^#+\s*', '', re.MULTILINE),         # Headings (e.g., ## Heading) - Use MULTILINE
            (r'^-?\s*', '', re.MULTILINE),         # List items (e.g., - item) - Use MULTILINE
            (r'^\s*>\s*', '', re.MULTILINE),       # Blockquotes (e.g., > quote) - Use MULTILINE
            (r'`{3}.*?`{3}', '', re.DOTALL),        # Code blocks (```code```) - Use DOTALL for multiline
            (r'`(.*?)`', r'\1'),                   # Inline code (`code`)
            (r'---\s*$', '', re.MULTILINE),         # Horizontal rules (---) at end of line
        ]

    def _strip_markdown(self, text: str) -> str:
        """Strips common markdown syntax from a given text."""
        for pattern, replacement, flags in self.markdown_patterns:
            text = re.sub(pattern, replacement, text, flags=flags if flags is not None else 0)
        return text

    def _extract_and_add_hashtags(self, text: str, bot_hashtag_keywords: List[str]) -> str:
        """
        Extracts existing hashtags and adds relevant bot keywords as hashtags,
        avoiding duplicates. Ensures hashtags are at the end.
        """
        existing_hashtags = set(re.findall(r'#(\w+)', text))
        clean_text = re.sub(r'#\w+\s*', '', text).strip() # Remove existing hashtags from text body

        # Add bot's keywords as hashtags, if not already present
        new_hashtags = []
        for keyword in bot_hashtag_keywords:
            if keyword.lower() not in [tag.lower() for tag in existing_hashtags]:
                new_hashtags.append(f"#{keyword}")
        
        # Combine existing unique hashtags with new ones, then add to text
        all_hashtags = sorted(list(existing_hashtags) + new_hashtags)
        if all_hashtags:
            return f"{clean_text} {' '.join(all_hashtags)}"
        return clean_text

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to max_chars, ensuring it ends cleanly."""
        if len(text) > max_chars:
            # Try to truncate at the last full word or sentence end
            truncated_text = text[:max_chars]
            last_space = truncated_text.rfind(' ')
            if last_space != -1:
                truncated_text = truncated_text[:last_space]
            return truncated_text.strip() + "..."
        return text

    def extract_tweet_and_image_prompt(self, raw_gemini_response: str) -> Tuple[str, Optional[str]]:
        """
        Extracts the main tweet content and an optional image generation prompt
        from Gemini's raw text response.

        Assumes the Gemini response might contain:
        - A main tweet text (can be markdown)
        - Optionally, a line starting with "IMAGE PROMPT: " for the image description.

        This version uses a more robust regex to account for variations in spacing
        and optional colon around "IMAGE PROMPT:".

        :param raw_gemini_response: The full text response from Gemini.
        :return: A tuple of (tweet_text, image_prompt_from_gemini).
        """
        log.debug(f"[extract_tweet_and_image_prompt] Raw Gemini response:\n---\n{raw_gemini_response}\n---")

        tweet_text = raw_gemini_response.strip() # Initialize with full response, will be modified
        image_prompt = None

        # Robust regex pattern:
        # \s* - Match any leading whitespace (including newlines)
        # IMAGE\s*PROMPT - Match "IMAGE PROMPT" with any whitespace between them
        # [:?]?      - Optionally match a colon (:) zero or one time
        # \s* - Match any whitespace after the colon/PROMPT
        # (.*)       - Capture everything that follows as the image prompt (non-greedy, with DOTALL)
        image_prompt_pattern = re.compile(r'\s*IMAGE\s*PROMPT\s*[:]?\s*(.*)', re.IGNORECASE | re.DOTALL)
        
        image_prompt_match = image_prompt_pattern.search(raw_gemini_response)

        if image_prompt_match:
            # The actual image prompt content is in the first capturing group
            image_prompt = image_prompt_match.group(1).strip()
            
            # The tweet text is everything *before* the start of the matched 'IMAGE PROMPT:' pattern.
            tweet_text = raw_gemini_response[:image_prompt_match.start()].strip()
            
            log.info(f"Detected image prompt: {image_prompt[:50]}...")
            log.info(f"Tweet text after removing image prompt: {tweet_text[:50]}...")
        else:
            log.info("No 'IMAGE PROMPT:' pattern found in Gemini response using robust regex.")
            # If no image prompt, tweet_text remains the full stripped raw_gemini_response.

        return tweet_text, image_prompt

    def format_for_twitter(self, raw_text: str, bot_id: int, relevant_themes: List[str]) -> str:
        """
        Formats a given text for a Twitter post. This method now primarily
        focuses on stripping markdown, adding hashtags, and truncating.
        The extraction of tweet and image prompt is handled by a separate method.
        :param raw_text: The text generated by Gemini (expected to be already extracted single tweet).\n
        :param bot_id: The ID of the bot (for potential platform config lookup).\n
        :param relevant_themes: List of current themes/keywords for the bot's journey (now bot's hashtag_keywords).\n
        :return: Formatted tweet string.
        """
        log.debug(f"[format_for_twitter] Input text (should be single tweet now):\\n---\\n{raw_text}\\n---")

        is_premium_account = self.platform_configs.get(f'{bot_id}_twitter_premium', False)
        max_chars = 25000 if is_premium_account else 280

        # The raw_text passed here is already expected to be the single tweet content
        # from extract_tweet_and_image_prompt.
        formatted_text = self._strip_markdown(raw_text)
        log.debug(f"[format_for_twitter] Formatted text after markdown strip:\\n---\\n{formatted_text}\\n---")

        text_with_hashtags = self._extract_and_add_hashtags(formatted_text, relevant_themes)
        log.debug(f"[format_for_twitter] Text with hashtags:\\n---\\n{text_with_hashtags}\\n---")

        final_tweet_text = self._truncate_text(text_with_hashtags, max_chars)

        log.debug(f"[format_for_twitter] Final tweet text: {final_tweet_text[:100]}...")
        return final_tweet_text