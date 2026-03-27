"""
Core agentic loop: user message → Claude → tool calls → tool results → Claude → final response.
Implements the multi-turn tool_use conversation pattern required by the Anthropic API.
"""
import json
import os
import anthropic
from agent_tools.tool_registry import TOOLS
from .tool_dispatcher import dispatch_tool

_CREDENTIALS_PATH = os.path.expanduser("~/.claude/.credentials.json")


def _get_api_key() -> str:
    """
    Return the Anthropic API key.
    Prefers the live OAuth token from Claude Code's credentials file (auto-refreshed),
    falling back to ANTHROPIC_API_KEY env var.
    """
    try:
        with open(_CREDENTIALS_PATH) as f:
            creds = json.load(f)
        token = creds.get("claudeAiOauth", {}).get("accessToken", "")
        if token:
            return token
    except Exception:
        pass
    return os.environ["ANTHROPIC_API_KEY"]


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=_get_api_key())


SYSTEM_PROMPT = """You are Pocket IA, an AI-powered Wealth Management assistant for Relationship Managers (RMs).
You have LIVE access to client data via tools. ALWAYS call a tool first — never say you lack access.

DATA SOURCES:
- Zoho CRM          → client profiles: name, risk profile, AUM, investment objectives, last meeting date
- PostgreSQL         → holdings (positions), portfolio_snapshots (analytics), policies (insurance)

TOOL SELECTION — match any of these patterns and call the tool immediately, no clarification needed:

query_clients — use when:
  • "list/show/give me (all) clients"
  • "which clients / who has / how many clients"
  • "clients with AUM above/below/over/under X" — convert any format: "$10M"=10000000, "10 mil"=10000000, "10 million"=10000000, "10k"=10000
  • "conservative / moderate / aggressive clients" or "clients by risk profile"
  • any question filtering or counting clients by any attribute

query_clients THEN query_portfolio — use when:
  • "[client name] portfolio / allocation / holdings / sectors / geography / risk / performance"
  • "what does [client] hold", "how is [client] invested"

query_clients THEN query_policies — use when:
  • "[client name] policies / insurance / coverage / premium / renewal"
  • "does [client] have insurance"

get_client_full_profile — use when:
  • "tell me about / overview / summary / profile of [client]"
  • "everything about [client]", "give me [client] details"
  • general question about a client with no specific data type mentioned

query_policies — use when:
  • "all policies", "show policies", "list insurance"
  • "policies renewing in X days/weeks", "upcoming renewals"
  • "[client] policies" (resolve name → ID first)

query_unmet_clients — use when:
  • "not met in X days/weeks", "overdue meetings", "follow-up needed"
  • "who needs a visit", "meeting cadence", "clients I haven't seen"
  • default to 30 days; use 14 for "two weeks" / "2 weeks"

market_impact_analyzer — use when:
  • "who is exposed to [event]", "impact of [market event]"
  • "rate hike / selloff / crash / slowdown — which clients affected"
  • "tech exposure", "bond exposure across clients"

CLIENT NAME RESOLUTION:
  Known clients: East Asia (CLI001), Euro Alpine (CLI002), Family Office (CLI003),
  Gulf Capital (CLI004), Indian Custodian (CLI005), Northern Trust (CLI006), Pacific Bridge (CLI007).
  If a name is mentioned, use query_clients(name_contains=<last word>) to get the CLI ID first.

RESPONSE FORMAT — Slack mrkdwn only, strictly follow these rules:
- Bold: *text* (single asterisk). Never use **double asterisk**.
- Italic: _text_ (underscore).
- Never use markdown tables (| col | col |) — Slack does not render them.
- Instead of tables, use labelled bullet lines: • *Client:* East Asia | *AUM:* $15.8M | *Risk:* Moderate
- Section headers: use *ALL CAPS HEADER* on its own line, followed by a blank line.
- Bullet points: use • (bullet character), not - or *.
- Numbers/amounts: always format with commas and $ sign e.g. $15,760,701 or $15.8M.
- Dividers between sections: use a line of ─────────────────
- Keep responses concise. No walls of text.
- Always state as_of_date for portfolio data.
- Flag risks inline: ⚠️ concentration >40%, ⚠️ renewal within 90 days, ⚠️ meeting overdue >30 days."""

MAX_TOOL_ROUNDS = 10  # prevent infinite loops


def run_claude_loop(user_message: str, conversation_history: list = None) -> tuple[str, list]:
    """
    Run the agentic tool call loop.

    Args:
        user_message: The RM's query from Slack.
        conversation_history: Prior conversation turns for multi-turn context.

    Returns:
        (response_text, updated_history) tuple.
    """
    client = get_client()
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Append Claude's response to conversation history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text_blocks = [
                block.text
                for block in response.content
                if hasattr(block, "text") and block.type == "text"
            ]
            reply = "\n".join(text_blocks).strip() or "I wasn't able to generate a response."
            return reply, messages

        if response.stop_reason == "tool_use":
            # Execute every tool Claude requested and collect results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_content = dispatch_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_content,
                    })

            # Feed tool results back as a user turn
            messages.append({"role": "user", "content": tool_results})

        else:
            reply = f"Response was cut short (stop_reason={response.stop_reason}). Please try a more specific question."
            return reply, messages

    reply = "I reached the maximum number of tool calls. Please try a more focused question."
    return reply, messages
