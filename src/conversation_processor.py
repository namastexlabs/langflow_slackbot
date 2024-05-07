# slack_ai_assistant/conversation_processor.py
import json
import requests
from file_utils import save_uploaded_file, clean_up_file, generate_random_file_name
from openai_config import get_ai_client
from logging_config import logger
from config import Config
from openai_utils import *

ai_client = get_ai_client()

def process_conversation(client, message, tools):
    conversation_history = get_conversation_history(client, message)
    result = get_gpt_response(ai_client, Config.GPT_MODEL, Config.SYSTEM_PROMPT, conversation_history, tools)
    logger.info(f'GPT response: {result}')
    response = None

    if result.content:
        response = result.content
    elif result.tool_calls:
        function_name = result.tool_calls[0].function.name
        arguments = json.loads(result.tool_calls[0].function.arguments)
        logger.info(f'Tool called: {function_name} with arguments: {arguments}')
        if function_name == "generate_image":
            description = arguments["description"]
            size = arguments.get("size", "square")
            try:
                image_url = generate_image(ai_client, Config.IMAGE_MODEL, description, size)
                image_content = requests.get(image_url)
                image_filepath = f'{Config.TEMP_FILES_FOLDER}/{generate_random_file_name()}.jpg'
                with open(image_filepath, "wb") as f:
                    f.write(image_content.content)
                client.files_upload_v2(channel=message["channel"], thread_ts=message["ts"], file=image_filepath, title=description)
                response = None
                clean_up_file(image_filepath)
            except Exception as e:
                response = f'[ERROR] Problem generating image using DALL-E:\n {e}'
        elif function_name == "generate_tts":
            input_text = arguments["input_text"]
            try:
                generated_file = generate_tts(ai_client, Config.TEMP_FILES_FOLDER, Config.TTS_MODEL, Config.TTS_VOICE, input_text)
                client.files_upload_v2(channel=message["channel"], thread_ts=message["ts"], file=generated_file, title="Text To Speech")
                response = None
                clean_up_file(generated_file)
            except Exception as e:
                response = f'[ERROR] Problem converting from text to speech:\n {e}'
        elif function_name == "generate_stt":
            try:
                file_path = save_uploaded_file(message["files"][0], Config.SLACK_BOT_USER_TOKEN)
                logger.info(f"Processing audio file: {file_path}")
                transcript = generate_stt(ai_client, file_path, Config.STT_MODEL)
                clean_up_file(file_path)
                response = f'Transcript of the audio:\n{transcript}'
                logger.info(f"Audio processed and response generated: {response}")
            except Exception as e:
                response = f'[ERROR] Problem converting from speech to text:\n {e}'
                logger.error(response)
    return response

def get_conversation_history(client, message):
    result = []
    if "thread_ts" in message:
        conversation = client.conversations_replies(channel=message["channel"], ts=message["thread_ts"])
        if "messages" in conversation:
            for msg in conversation["messages"]:
                if "client_msg_id" in msg:
                    gpt_message = create_gpt_user_message_from_slack_message(msg)
                    result.append(gpt_message)
                if "bot_id" in msg and msg["text"] != Config.WAITING_MESSAGE:
                    result.append({"role": "assistant", "content": msg["text"]})
    else:
        gpt_message = create_gpt_user_message_from_slack_message(message)
        result.append(gpt_message)
    return result

def create_gpt_user_message_from_slack_message(slack_message):
    if "files" in slack_message:
        attached_file = slack_message["files"][0]
        if attached_file["filetype"].lower() in ["png", "jpg", "jpeg", "gif", "webp"]:
            image_file = save_uploaded_file(attached_file, Config.SLACK_BOT_USER_TOKEN)
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
            audio_file = save_uploaded_file(attached_file, Config.SLACK_BOT_USER_TOKEN)
            transcript = generate_stt(ai_client, audio_file, Config.STT_MODEL)
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