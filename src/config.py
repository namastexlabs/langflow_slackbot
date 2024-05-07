# slack_ai_assistant/config.py
import os
from dotenv import load_dotenv
from slack_bolt import App

load_dotenv()

class Config:
    SLACK_SOCKET_TOKEN = os.getenv("SLACK_SOCKET_TOKEN")
    SLACK_BOT_USER_TOKEN = os.getenv("SLACK_BOT_USER_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    TRIGGER_WORD = os.getenv("TRIGGER_WORD", "lang")
    app = App(token = SLACK_BOT_USER_TOKEN)

    OPENAI_KEY = os.getenv("OPENAI_KEY")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_VERSION")

    WAITING_MESSAGE = os.getenv("WAITING_MESSAGE")
    SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
    TEMP_FILES_FOLDER = os.getenv("TEMP_FILES_FOLDER")

    IMAGE_GENERATION_ENABLED = os.getenv('IMAGE_GENERATION_ENABLED', 'False').lower() in ('true', '1')
    TEXT_TO_SPEECH_ENABLED = os.getenv('TEXT_TO_SPEECH_ENABLED', 'False').lower() in ('true', '1')
    SPEECH_TO_TEXT_ENABLED = os.getenv('SPEECH_TO_TEXT_ENABLED', 'False').lower() in ('true', '1')

    GPT_MODEL = os.getenv("GPT_MODEL")
    TTS_MODEL = os.getenv("TTS_MODEL")
    TTS_VOICE = os.getenv("TTS_VOICE")
    IMAGE_MODEL = os.getenv("IMAGE_MODEL")
    STT_MODEL = os.getenv("STT_MODEL")