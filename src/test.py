from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


SLACK_SOCKET_TOKEN = os.getenv("SLACK_SOCKET_TOKEN")
SLACK_BOT_USER_TOKEN = os.getenv("SLACK_BOT_USER_TOKEN")
SLACK_SIGNING_SECRET=os.environ.get("SLACK_SIGNING_SECRET")

app = App(token=SLACK_BOT_USER_TOKEN)

@app.event("*")
def handle_all_events(body, logger):
    event_type = body["type"]
    event_data = body["event"]
    logger.info(f"Event received: [Type: {event_type}, Data: {event_data}]")

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_SOCKET_TOKEN)
    handler.start()