# slack_ai_assistant/event_handlers.py
from conversation_processor import process_conversation
from file_utils import save_uploaded_file, clean_up_file
from openai_config import get_ai_client
from logging_config import logger, HANDLED_MESSAGE_LEVEL, UNHANDLED_MESSAGE_LEVEL, BOT_RESPONSE_LEVEL
from config import Config
from openai_utils import *
from slack_bolt import App
from dotenv import load_dotenv
import os
load_dotenv()  # This will load all the environment variables from a .env file located in the same directory as the script.
SLACK_BOT_USER_TOKEN = os.getenv("SLACK_BOT_USER_TOKEN")

ai_client = get_ai_client()
app = App(token = SLACK_BOT_USER_TOKEN)

def handle_audio_and_respond(client, event):
    logger.info(f"handle_audio_and_respond called with event: {event}")
    if "files" in event:
        for file in event["files"]:
            if file["filetype"] in ["mp3", "wav", "ogg", "flac", "webm"]:
                try:
                    file_path = save_uploaded_file(file, Config.SLACK_BOT_USER_TOKEN)
                    logger.info(f"Processing audio file: {file_path}")
                    transcript = generate_stt(ai_client, file_path, Config.STT_MODEL)
                    clean_up_file(file_path)
                    response_text = process_conversation(client, {"text": transcript, "channel": event["channel"], "ts": event["ts"]}, get_tools())
                    response = f'Transcript of the audio:\n{transcript}\n\nResponse:\n{response_text}'
                    logger.info(f"Audio processed and response generated: {response}")
                except Exception as e:
                    response = f'[ERROR] Problem converting from speech to text:\n {e}'
                    logger.error(response)
                
                if "thread_ts" in event:
                    client.chat_postMessage(channel=event["channel"], thread_ts=event["thread_ts"], text=response)
                else:
                    client.chat_postMessage(channel=event["channel"], text=response)
                
                logger.log(BOT_RESPONSE_LEVEL, f'Audio response sent: {response}')
                return True  # Indicates that an audio file was processed
    return False  # No audio file processed

@app.event("message")
def handle_message_events(client, body):
    event = body.get('event', {})
    if event.get('channel_type') == 'im':
        if event.get('subtype') == 'file_share':
            logger.info(f"Received file share event in DM: {event}")
            client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")
            
            if "files" in event:
                for file in event["files"]:
                    if file["filetype"] in ["png", "jpg", "jpeg", "gif", "webp", "mp3", "wav", "ogg", "flac", "webm"]:
                        try:
                            response = process_conversation(client, event, get_tools())
                            logger.info(f"File processed and response generated: {response}")
                        except Exception as e:
                            response = f'[ERROR] Problem processing file:\n {e}'
                            logger.error(response)
                        
                        client.chat_postMessage(channel=event["channel"], text=response)
                        logger.log(BOT_RESPONSE_LEVEL, f'File response sent: {response}')
                        client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
                        return  # Exit after processing the file
        else:
            logger.info(f"DM event: {event}")
            client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")
            logger.log(HANDLED_MESSAGE_LEVEL, f'Handling DM: {event}')
            response = process_conversation(client, event, get_tools())
            if response:  # This checks if response is not None or not an empty string
                message_kwargs = {
                    "channel": event["channel"],
                    "text": response
                }
                if "thread_ts" in event:
                    message_kwargs["thread_ts"] = event["thread_ts"]
                client.chat_postMessage(**message_kwargs)
            logger.log(BOT_RESPONSE_LEVEL, f'DM reply: {response}')
            client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
    elif "thread_ts" in event and event["parent_user_id"] == client.auth_test()["user_id"]:
        client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")
        logger.log(HANDLED_MESSAGE_LEVEL, f'Handling thread reply: {event}')
        if not handle_audio_and_respond(client, event):
            response = process_conversation(client, {"text": event["text"], "channel": event["channel"], "ts": event["thread_ts"]}, get_tools())
            client.chat_postMessage(channel=event["channel"], thread_ts=event["thread_ts"], text=response)
            logger.log(BOT_RESPONSE_LEVEL, f'Thread reply: {response}')
        client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
    elif event["channel_type"] == "channel":
        if Config.TRIGGER_WORD.lower() in event["text"].lower():
            client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")
            logger.log(HANDLED_MESSAGE_LEVEL, f'Handling trigger word "{Config.TRIGGER_WORD}": {event}')
            if not handle_audio_and_respond(client, event):
                response = process_conversation(client, event, get_tools())
                logger.log(BOT_RESPONSE_LEVEL, f'Trigger word reply: {response}')
            client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
        else:
            # Regular channel message, not intended for the bot
            logger.log(UNHANDLED_MESSAGE_LEVEL, f"Message Type: {event.get('channel_type')}, User: {event.get('user')}, Message: {event.get('text')}")
            
@app.event("app_mention")
def handle_app_mention_events(client, body):
    event = body.get('event', {})
    logger.log(HANDLED_MESSAGE_LEVEL, f'App mentioned: {event}')
    client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")

    # Check if there are files in the mention
    if "files" in event:
        for file in event["files"]:
            if file["filetype"] in ["mp3", "wav", "ogg", "flac", "webm"]:
                try:
                    file_path = save_uploaded_file(file, Config.SLACK_BOT_USER_TOKEN)
                    logger.info(f"Calling generate_stt with file: {file_path}")
                    transcript = generate_stt(ai_client, file_path, Config.STT_MODEL)
                    clean_up_file(file_path)
                    
                    # Generate a response using the transcript
                    response_text = process_conversation(client, {"text": transcript, "channel": event["channel"], "ts": event["ts"]}, get_tools())
                    response = f'Transcript of the audio:\n{transcript}\n\nResponse:\n{response_text}'
                    
                except Exception as e:
                    response = f'[ERROR] Problem converting from speech to text:\n {e}'
                client.chat_postMessage(channel=event["channel"], thread_ts=event["ts"], text=response)
                logger.log(BOT_RESPONSE_LEVEL, f'Mention reply with file: {response}')
                client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
                return  # Ensure we exit after handling the file
    # If no files, process the text mention
    response = process_conversation(client, event, get_tools())
    client.chat_postMessage(channel=event["channel"], thread_ts=event["ts"], text=response)
    logger.log(BOT_RESPONSE_LEVEL, f'Mention reply: {response}')
    client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")

def get_tools():
    tools = []
    if Config.IMAGE_GENERATION_ENABLED:
        tools.append({
            "type": "function",
            "function": {
                "name": "generate_image",
                "description": "Generate image basing on description",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Description of the image, e.g. a house under an apple tree",
                        },
                        "size": {
                            "type": "string",
                            "enum": ["square", "portrait", "landscape"],
                            "description": "Size of the generated image. Use square if no information is provided",
                        }
                    },
                    "required": ["description"],
                },
            },
        })
        logger.info('IMAGE_GENERATION: Enabled')
        
    else:
        logger.info('IMAGE_GENERATION: Disabled')

    if Config.TEXT_TO_SPEECH_ENABLED:
        tools.append({
            "type": "function",
            "function": {
                "name": "generate_tts",
                "description": "Generate or convert from text to speech",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_text": {
                            "type": "string",
                            "description": "Text to be converted to speech",
                        }
                    },
                    "required": ["input_text"],
                },
            },
        })
        logger.info('TEXT_TO_SPEECH: Enabled')
    else:
        logger.info('TEXT_TO_SPEECH: Disabled')

    if Config.SPEECH_TO_TEXT_ENABLED:
        tools.append({
            "type": "function",
            "function": {
                "name": "generate_stt",
                "description": "Transcript or convert from speech to text",
                "parameters": {
                    "type": "object",
                    "properties": {
                    }
                },
            },
        })
        logger.info('SPEECH_TO_TEXT: Enabled')
    else:
        logger.info('SPEECH_TO_TEXT: Disabled')

    return tools