"""
Slack message handler: routes incoming DMs and @mentions to the Claude loop.

Conversation history is kept per channel (in-memory).
Type /clear to wipe the history for the current channel.
"""
import re
from slack_bolt import App
from slack_sdk.errors import SlackApiError
from slack_bot.claude_loop import run_claude_loop

# Per-channel conversation history: {channel_id: [{"role": ..., "content": ...}, ...]}
_history: dict[str, list] = {}


def register_message_handler(app: App):
    @app.event("app_mention")
    def handle_mention(event, client, logger):
        """Handle @PocketIA mentions in channels."""
        _process_message(event, client, logger)

    @app.message("")
    def handle_direct_message(message, client, logger):
        """Handle direct messages to the bot."""
        if message.get("bot_id") or message.get("channel_type") != "im":
            return
        _process_message(message, client, logger)


def _process_message(event: dict, client, logger):
    channel = event.get("channel")
    user_text = event.get("text", "").strip()

    # Remove bot mention prefix e.g. "<@U12345> ..."
    user_text = re.sub(r"<@[A-Z0-9]+>\s*", "", user_text).strip()

    if not user_text:
        client.chat_postMessage(
            channel=channel,
            text="Hi! I'm Pocket IA. Ask me about client portfolios, policies, or market impacts.\nType */clear* to reset our conversation.",
        )
        return

    # /clear command — wipe history for this channel
    if user_text.lower() in ("/clear", "clear"):
        _history.pop(channel, None)
        client.chat_postMessage(
            channel=channel,
            text=":broom: Conversation history cleared. Starting fresh!",
        )
        return

    # Show hourglass reaction while thinking
    try:
        client.reactions_add(channel=channel, name="hourglass_flowing_sand", timestamp=event["ts"])
    except SlackApiError:
        pass

    # Post a loading placeholder
    loading_ts = None
    try:
        loading_resp = client.chat_postMessage(channel=channel, text=":hourglass_flowing_sand: Thinking...")
        loading_ts = loading_resp["ts"]
    except SlackApiError:
        pass

    try:
        history = _history.setdefault(channel, [])
        response_text, updated_history = run_claude_loop(user_text, history)
        _history[channel] = updated_history

        if loading_ts:
            try:
                client.chat_update(channel=channel, ts=loading_ts, text=response_text)
            except SlackApiError:
                client.chat_postMessage(channel=channel, text=response_text)
        else:
            client.chat_postMessage(channel=channel, text=response_text)

    except Exception as e:
        logger.error(f"Claude loop error: {e}", exc_info=True)
        error_text = f":warning: *{type(e).__name__}*: `{str(e)[:300]}`"
        if loading_ts:
            try:
                client.chat_update(channel=channel, ts=loading_ts, text=error_text)
            except SlackApiError:
                client.chat_postMessage(channel=channel, text=error_text)
        else:
            client.chat_postMessage(channel=channel, text=error_text)
    finally:
        try:
            client.reactions_remove(channel=channel, name="hourglass_flowing_sand", timestamp=event["ts"])
        except SlackApiError:
            pass
