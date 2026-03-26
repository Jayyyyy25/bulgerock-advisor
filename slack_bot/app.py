"""
Pocket IA Slack Bot — entry point.

Run with:
    python -m slack_bot.app
"""
import logging
import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .handlers.message_handler import register_message_handler
from .scheduler import start_scheduler

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> App:
    app = App(token=os.environ["SLACK_BOT_TOKEN"])
    register_message_handler(app)
    return app


if __name__ == "__main__":
    logger.info("Starting Pocket IA Slack bot...")
    app = create_app()

    # Start proactive alert scheduler
    scheduler = start_scheduler(app.client)

    # Start Socket Mode handler (keeps connection alive)
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    try:
        handler.start()
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
