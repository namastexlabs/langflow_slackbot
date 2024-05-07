# slack_ai_assistant/logging_config.py
import logging
from colorlog import ColoredFormatter

# Custom log levels
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

logger = logging.getLogger(__name__)