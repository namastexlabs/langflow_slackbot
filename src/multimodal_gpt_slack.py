from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from openai import OpenAI, AzureOpenAI
import requests
import os
import json
import re
import uuid
from openai_utils import *
from dotenv import load_dotenv
load_dotenv()  # This will load all the environment variables from a .env file located in the same directory as the script.

import logging
from colorlog import ColoredFormatter

# Define custom log levels
HANDLED_MESSAGE_LEVEL = 25
UNHANDLED_MESSAGE_LEVEL = 35
BOT_RESPONSE_LEVEL = 45

logging.addLevelName(HANDLED_MESSAGE_LEVEL, 'HANDLED_MESSAGE')
logging.addLevelName(UNHANDLED_MESSAGE_LEVEL, 'UNHANDLED_MESSAGE')
logging.addLevelName(BOT_RESPONSE_LEVEL, 'BOT_RESPONSE')

# Configure logging with colors
log_format = '%(log_color)s%(asctime)s - %(levelname)s - %(message)s'
log_colors = {
    'DEBUG': 'cyan',
    'INFO': 'white',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
    'HANDLED_MESSAGE': 'green',
    'UNHANDLED_MESSAGE': 'yellow',
    'BOT_RESPONSE': 'cyan',
}

formatter = ColoredFormatter(log_format, log_colors=log_colors)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

file_handler = logging.FileHandler('slack_bot.log')
file_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler]
)

SLACK_SOCKET_TOKEN = os.getenv("SLACK_SOCKET_TOKEN")
SLACK_BOT_USER_TOKEN = os.getenv("SLACK_BOT_USER_TOKEN")
SLACK_SIGNING_SECRET=os.environ.get("SLACK_SIGNING_SECRET")
TRIGGER_WORD = os.getenv("TRIGGER_WORD", "lang")  # Default to "lang" if not specified

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

app = App(token = SLACK_BOT_USER_TOKEN)
if OPENAI_KEY:
    print("Running with OpenAI")
    ai_client = OpenAI(api_key=OPENAI_KEY)
elif AZURE_OPENAI_KEY:
    print("Running with Azure OpenAI")
    ai_client = AzureOpenAI(api_key = AZURE_OPENAI_KEY, api_version=AZURE_OPENAI_VERSION, azure_endpoint=AZURE_OPENAI_ENDPOINT)
else:
    print("[ERROR] Missing both OPENAI_KEY and AZURE_OPENAI_KEY")
    exit(1)

tools = []
if IMAGE_GENERATION_ENABLED:
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
    print('IMAGE_GENERATION: Enabled')
    
else:
    print('IMAGE_GENERATION: Disabled')

if TEXT_TO_SPEECH_ENABLED:
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
    print('TEXT_TO_SPEECH: Enabled')
else:
    print('TEXT_TO_SPEECH: Disabled')

if SPEECH_TO_TEXT_ENABLED:
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
    print('SPEECH_TO_TEXT: Enabled')
else:
    print('SPEECH_TO_TEXT: Disabled')


def handle_audio_and_respond(client, event):
    logging.info(f"handle_audio_and_respond called with event: {event}")
    if "files" in event:
        for file in event["files"]:
            if file["filetype"] in ["mp3", "wav", "ogg", "flac", "webm"]:
                try:
                    file_path = save_uploaded_file(file)
                    logging.info(f"Processing audio file: {file_path}")
                    transcript = generate_stt(ai_client, file_path, STT_MODEL)
                    clean_up_file(file_path)
                    response_text = process_conversation(client, {"text": transcript, "channel": event["channel"], "ts": event["ts"]})
                    response = f'Transcript of the audio:\n{transcript}\n\nResponse:\n{response_text}'
                    logging.info(f"Audio processed and response generated: {response}")
                except Exception as e:
                    response = f'[ERROR] Problem converting from speech to text:\n {e}'
                    logging.error(response)
                
                if "thread_ts" in event:
                    client.chat_postMessage(channel=event["channel"], thread_ts=event["thread_ts"], text=response)
                else:
                    client.chat_postMessage(channel=event["channel"], text=response)
                
                logging.log(BOT_RESPONSE_LEVEL, f'Audio response sent: {response}')
                return True  # Indicates that an audio file was processed
    return False  # No audio file processed

@app.event("message")
def handle_message_events(client, body):
    event = body.get('event', {})
    if event.get('channel_type') == 'im':
        if event.get('subtype') == 'file_share':
            logging.info(f"Received file share event in DM: {event}")
            client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")
            
            if "files" in event:
                for file in event["files"]:
                    if file["filetype"] in ["png", "jpg", "jpeg", "gif", "webp", "mp3", "wav", "ogg", "flac", "webm"]:
                        try:
                            response = process_conversation(client, event)
                            logging.info(f"File processed and response generated: {response}")
                        except Exception as e:
                            response = f'[ERROR] Problem processing file:\n {e}'
                            logging.error(response)
                        
                        client.chat_postMessage(channel=event["channel"], text=response)
                        logging.log(BOT_RESPONSE_LEVEL, f'File response sent: {response}')
                        client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
                        return  # Exit after processing the file
        else:
            logging.info(f"DM event: {event}")
            client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")
            logging.log(HANDLED_MESSAGE_LEVEL, f'Handling DM: {event}')
            response = process_conversation(client, event)
            if response:  # This checks if response is not None or not an empty string
                message_kwargs = {
                    "channel": event["channel"],
                    "text": response
                }
                if "thread_ts" in event:
                    message_kwargs["thread_ts"] = event["thread_ts"]
                client.chat_postMessage(**message_kwargs)
            logging.log(BOT_RESPONSE_LEVEL, f'DM reply: {response}')
            client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
    elif "thread_ts" in event and event["parent_user_id"] == client.auth_test()["user_id"]:
        client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")
        logging.log(HANDLED_MESSAGE_LEVEL, f'Handling thread reply: {event}')
        if not handle_audio_and_respond(client, event):
            response = process_conversation(client, {"text": event["text"], "channel": event["channel"], "ts": event["thread_ts"]})
            client.chat_postMessage(channel=event["channel"], thread_ts=event["thread_ts"], text=response)
            logging.log(BOT_RESPONSE_LEVEL, f'Thread reply: {response}')
        client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
    elif event["channel_type"] == "channel":
        if "lang" in event["text"].lower():
            client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")
            logging.log(HANDLED_MESSAGE_LEVEL, f'Handling trigger word "lang": {event}')
            if not handle_audio_and_respond(client, event):
                response = process_conversation(client, event)
                logging.log(BOT_RESPONSE_LEVEL, f'Trigger word reply: {response}')
            client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
        else:
            # Regular channel message, not intended for the bot
            logging.log(UNHANDLED_MESSAGE_LEVEL, f"Message Type: {event.get('channel_type')}, User: {event.get('user')}, Message: {event.get('text')}")
@app.event("app_mention")
def handle_app_mention_events(client, body):
    event = body.get('event', {})
    logging.log(HANDLED_MESSAGE_LEVEL, f'App mentioned: {event}')
    client.reactions_add(channel=event["channel"], timestamp=event["ts"], name="sparkles")

    # Check if there are files in the mention
    if "files" in event:
        for file in event["files"]:
            if file["filetype"] in ["mp3", "wav", "ogg", "flac", "webm"]:
                try:
                    file_path = save_uploaded_file(file)
                    logging.info(f"Calling generate_stt with file: {file_path}")
                    transcript = generate_stt(ai_client, file_path, STT_MODEL)
                    clean_up_file(file_path)
                    
                    # Generate a response using the transcript
                    response_text = process_conversation(client, {"text": transcript, "channel": event["channel"], "ts": event["ts"]})
                    response = f'Transcript of the audio:\n{transcript}\n\nResponse:\n{response_text}'
                    
                except Exception as e:
                    response = f'[ERROR] Problem converting from speech to text:\n {e}'
                client.chat_postMessage(channel=event["channel"], thread_ts=event["ts"], text=response)
                logging.log(BOT_RESPONSE_LEVEL, f'Mention reply with file: {response}')
                client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
                return  # Ensure we exit after handling the file
    # If no files, process the text mention
    response = process_conversation(client, event)
    client.chat_postMessage(channel=event["channel"], thread_ts=event["ts"], text=response)
    logging.log(BOT_RESPONSE_LEVEL, f'Mention reply: {response}')
    client.reactions_remove(channel=event["channel"], timestamp=event["ts"], name="sparkles")
#============================================#
def process_conversation(client, message):
    conversation_history = get_conversation_history(client, message)
    result = get_gpt_response(ai_client, GPT_MODEL, SYSTEM_PROMPT, conversation_history, tools)
    logging.info(f'GPT response: {result}')
    if result.content:
        response = result.content
    elif result.tool_calls:
        function_name = result.tool_calls[0].function.name
        arguments = json.loads(result.tool_calls[0].function.arguments)
        logging.info(f'Tool called: {function_name} with arguments: {arguments}')
        if function_name == "generate_image":
            description = arguments["description"]
            try:
                size = arguments["size"]
            except:
                size = "square"
            try:
                image_url = generate_image(ai_client, IMAGE_MODEL, description, size)
                image_content = requests.get(image_url)
                image_filepath = f'{TEMP_FILES_FOLDER}/{generate_random_file_name()}.jpg'
                with open(image_filepath, "wb") as f:
                    f.write(image_content.content)
                client.files_upload_v2(channel = message["channel"], thread_ts = message["ts"], file = image_filepath, title = description)
                response = None
                clean_up_file(image_filepath)
            except Exception as e:
                response = f'[ERROR] Problem generating image using DALL-E:\n {e}'
        elif function_name == "generate_tts":
            input_text = arguments["input_text"]
            try:
                generated_file = generate_tts(ai_client, TEMP_FILES_FOLDER, TTS_MODEL, TTS_VOICE, input_text)
                client.files_upload_v2(channel = message["channel"], thread_ts = message["ts"], file = generated_file, title = "Text To Speech")
                response = None
                clean_up_file(generated_file)
            except Exception as e:             
                response = f'[ERROR] Problem converting from text to speech:\n {e}'
    return response

def get_conversation_history(client, message):
    result = []
    if "thread_ts" in message:
        conversation = client.conversations_replies(channel = message["channel"], ts = message["thread_ts"])
        if "messages" in conversation:
            for msg in conversation["messages"]:
                if "client_msg_id" in msg:
                    gpt_message = create_gpt_user_message_from_slack_message(msg)
                    result.append(gpt_message)
                if "bot_id" in msg:
                    if msg["text"] != WAITING_MESSAGE:
                        result.append({"role": "assistant", "content": msg["text"]})
    else:
        gpt_message = create_gpt_user_message_from_slack_message(message)
        result.append(gpt_message)
    return result

def save_uploaded_file(file):
    url = file["url_private"]
    headers = {"Authorization": "Bearer " + SLACK_BOT_USER_TOKEN}
    response = requests.get(url, headers=headers)
    file_extension = file["filetype"]
    file_path = f'{TEMP_FILES_FOLDER}/{generate_random_file_name()}.{file_extension}'
    with open(file_path, "wb") as f:
        f.write(response.content)
    logging.info(f"File saved: {file_path}")
    return file_path

def create_gpt_user_message_from_slack_message(slack_message):
    if "files" in slack_message:
        attached_file = slack_message["files"][0]
        if attached_file["filetype"].lower() in ["png", "jpg", "jpeg", "gif", "webp"]:
            image_file = save_uploaded_file(attached_file)
            base64_image = encode_image(image_file)
            result = {
                "role": "user",
                "content": [
                    {"type": "text", "text": slack_message["text"]},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }
            clean_up_file(image_file)
        elif attached_file["filetype"].lower() in ["mp3", "wav", "ogg", "flac"]:
            audio_file = save_uploaded_file(attached_file)
            transcript = generate_stt(ai_client, audio_file, STT_MODEL)
            result = {
                "role": "user",
                "content": [
                    {"type": "text", "text": slack_message["text"]},
                    {"type": "text", "text": f"Transcript of the audio:\n{transcript}"},
                ],
            }
            clean_up_file(audio_file)
        else:
            result = {"role": "user", "content": slack_message["text"]}
    else:
        result = {"role": "user", "content": slack_message["text"]}
    return result

def clean_up_file(file_path):
    os.remove(file_path)

def generate_random_file_name():
    return str(uuid.uuid4())

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_SOCKET_TOKEN)
    handler.start()