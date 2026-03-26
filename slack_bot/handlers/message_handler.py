"""
Slack message handler: routes incoming DMs and @mentions to the Claude loop.
"""
from slack_bolt import App
from slack_sdk.errors import SlackApiError
from slack_bot.claude_loop import run_claude_loop


def register_message_handler(app: App):
    @app.event("app_mention")
    def handle_mention(event, client, logger):
        """Handle @PocketIA mentions in channels."""
        _process_message(event, client, logger)

    @app.message("")
    def handle_direct_message(message, client, logger):
        """Handle direct messages to the bot."""
        # Skip bot's own messages and messages in channels (handled by mention)
        if message.get("bot_id") or message.get("channel_type") != "im":
            return
        _process_message(message, client, logger)


def _process_message(event: dict, client, logger):
    channel = event.get("channel")
    user_text = event.get("text", "").strip()

    # Remove the bot mention prefix if present (e.g., "<@U12345> show me...")
    import re
    user_text = re.sub(r"<@[A-Z0-9]+>\s*", "", user_text).strip()

    if not user_text:
        client.chat_postMessage(
            channel=channel,
            text="Hi! I'm Pocket IA. Ask me about client portfolios, policies, or market impacts.",
        )
        return

    # Show a typing reaction while processing
    try:
        client.reactions_add(channel=channel, name="hourglass_flowing_sand", timestamp=event["ts"])
    except SlackApiError:
        pass  # Reaction is a nice-to-have, not critical

    # Post a visible loading message in the main chat
    loading_ts = None
    try:
        loading_resp = client.chat_postMessage(
            channel=channel,
            text=":hourglass_flowing_sand: Thinking...",
        )
        loading_ts = loading_resp["ts"]
    except SlackApiError:
        pass

    try:
        response_text = run_claude_loop(user_text)
        # Update the loading message in-place with the real response
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
            client.reactions_remove(channel=channel, name="hourglass_flowing_sand",
                                    timestamp=event["ts"])
        except SlackApiError:
            pass
