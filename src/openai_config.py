# slack_ai_assistant/openai_config.py
from openai import OpenAI, AzureOpenAI
from config import Config

def get_ai_client():
    if Config.OPENAI_KEY:
        print("Running with OpenAI")
        return OpenAI(api_key=Config.OPENAI_KEY)
    elif Config.AZURE_OPENAI_KEY:
        print("Running with Azure OpenAI")
        return AzureOpenAI(
            api_key=Config.AZURE_OPENAI_KEY,
            api_version=Config.AZURE_OPENAI_VERSION,
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
        )
    else:
        print("[ERROR] Missing both OPENAI_KEY and AZURE_OPENAI_KEY")
        exit(1)