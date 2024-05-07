# slack_ai_assistant/slack_bot.py
from slack_bolt import App
from config import Config
from event_handlers import handle_message_events, handle_app_mention_events

def init_slack_bot():
    app = App(token=Config.SLACK_BOT_USER_TOKEN, signing_secret=Config.SLACK_SIGNING_SECRET)
    app.event("message")(handle_message_events)
    app.event("app_mention")(handle_app_mention_events)
    return app