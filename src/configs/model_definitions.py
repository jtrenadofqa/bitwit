# src/configs/model_definitions.py
# This file defines all AI models used by the application.
# It is meant to be version-controlled (committed to Git).

MODEL_DEFINITIONS = {
    "gemini-1.5-pro-latest": {
        "name": "gemini-1.5-pro-latest",
        "type": "generative_language_api_library", # Indicates use of google.generativeai library
        "description": "Google Gemini 1.5 Pro (latest) for general text generation with large context."
    },
    "gemini-1.0-pro": {
        "name": "gemini-1.0-pro",
        "type": "generative_language_api_library",
        "description": "Google Gemini 1.0 Pro for general text generation."
    },
    "gemini-1.5-flash": {
        "name": "gemini-1.5-flash",
        "type": "generative_language_api_library",
        "description": "Google Gemini 1.5 Flash for high-speed text generation."
    },
    "gemini-2.0-flash": {
        "name": "gemini-2.0-flash",
        "type": "generative_language_api_library",
        "description": "Google Gemini 2.0 Flash for high-speed text generation."
    },
    "imagen-3.0-generate-002": {
        "name": "imagen-3.0-generate-002",
        "type": "generative_language_api_direct_http", # Indicates direct HTTP requests as per your old image_utils
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models/",
        "description": "Google Imagen 3.0 for high-quality image generation via direct API."
    },
    # Add other models here as needed (e.g., another image model, a different text model)
}