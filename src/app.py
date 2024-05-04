
from fastapi import FastAPI
from api_handlers.message_handler import handle_message_events
from api_handlers.mention_handler import handle_app_mention_events
from api_handlers.file_handler import handle_file_events

app = FastAPI()

@app.post("/events/message/")
async def message_event():
    return handle_message_events()

@app.post("/events/mention/")
async def mention_event():
    return handle_app_mention_events()

@app.post("/events/file/")
async def file_event():
    return handle_file_events()
