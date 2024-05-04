
import requests
import json
import os

# Define a class to handle OpenAI integration
class OpenAIIntegration:
    def __init__(self):
        # Fetch the API key securely, assuming an environment variable exists for this purpose
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key for OpenAI is not defined in environment variables.")

    def process_conversation(self, message):
        """
        Process a conversation message using OpenAI's API.

        Parameters:
        message (str): the user's input message to process.

        Returns:
        str: the AI-generated response to the input message.
        """
        url = "https://api.openai.com/v1/engines/davinci-codex/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": message,
            "max_tokens": 150
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()  # raise exception for bad requests
            data = response.json()
            ai_response = data["choices"][0]["text"].strip() if data["choices"] else ''
            return ai_response
        except requests.exceptions.RequestException as e:
            print(f"Failed to get response from OpenAI: {e}")
            return "There was an error processing your request. Please try again later."

# Assuming other parts of the program might instantiate and use this
if __name__ == "__main__":
    ai_integration = OpenAIIntegration()
    sample_message = "Hello OpenAI, can you help me write better Python code?"
    response = ai_integration.process_conversation(sample_message)
    print("AI Response:", response)
