"""
Slack message handler: routes incoming DMs and @mentions to the Claude loop.
"""
from slack_bolt import App
from slack_sdk.errors import SlackApiError
from slack_bot.claude_loop import run_claude_loop


def register_message_handler(app: App):
    @app.event("app_mention")
    def handle_mention(event, say, client, logger):
        """Handle @PocketIA mentions in channels."""
        _process_message(event, say, client, logger)

    @app.message("")
    def handle_direct_message(message, say, client, logger):
        """Handle direct messages to the bot."""
        # Skip bot's own messages and messages in channels (handled by mention)
        if message.get("bot_id") or message.get("channel_type") != "im":
            return
        _process_message(message, say, client, logger)


def _process_message(event: dict, say, client, logger):
    channel = event.get("channel")
    thread_ts = event.get("thread_ts", event.get("ts"))
    user_text = event.get("text", "").strip()

    # Remove the bot mention prefix if present (e.g., "<@U12345> show me...")
    import re
    user_text = re.sub(r"<@[A-Z0-9]+>\s*", "", user_text).strip()

    if not user_text:
        say(text="Hi! I'm Pocket IA. Ask me about client portfolios, policies, or market impacts.",
            thread_ts=thread_ts)
        return

    # Show a typing reaction while processing
    try:
        client.reactions_add(channel=channel, name="hourglass_flowing_sand", timestamp=event["ts"])
    except SlackApiError:
        pass  # Reaction is a nice-to-have, not critical

    try:
        response_text = run_claude_loop(user_text)
        say(text=response_text, thread_ts=thread_ts)
    except Exception as e:
        logger.error(f"Claude loop error: {e}", exc_info=True)
        say(text=f":warning: *{type(e).__name__}*: `{str(e)[:300]}`",
            thread_ts=thread_ts)
    finally:
        try:
            client.reactions_remove(channel=channel, name="hourglass_flowing_sand",
                                    timestamp=event["ts"])
        except SlackApiError:
            pass
