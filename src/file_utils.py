# slack_ai_assistant/file_utils.py
import os
import requests
import uuid
from config import Config
from logging_config import logger

def save_uploaded_file(file, token):
    url = file["url_private"]
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    file_extension = file["filetype"]
    file_path = f'{Config.TEMP_FILES_FOLDER}/{generate_random_file_name()}.{file_extension}'
    with open(file_path, "wb") as f:
        f.write(response.content)
    logger.info(f"File saved: {file_path}")
    return file_path

def clean_up_file(file_path):
    os.remove(file_path)

def generate_random_file_name():
    return str(uuid.uuid4())