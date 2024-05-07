# slack_ai_assistant/main.py
from slack_bolt.adapter.socket_mode import SocketModeHandler
# main.py
from config import Config
from slack_bot import init_slack_bot

def main():
    app = init_slack_bot()
    handler = SocketModeHandler(app, Config.SLACK_SOCKET_TOKEN)
    handler.start()

if __name__ == "__main__":
    main()