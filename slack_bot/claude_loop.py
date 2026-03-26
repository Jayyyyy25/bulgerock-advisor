"""
Core agentic loop: user message → Claude → tool calls → tool results → Claude → final response.
Implements the multi-turn tool_use conversation pattern required by the Anthropic API.
"""
import os
import anthropic
from agent_tools.tool_registry import TOOLS
from .tool_dispatcher import dispatch_tool

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


SYSTEM_PROMPT = """You are Pocket IA, an AI-powered Wealth Management assistant for Relationship Managers (RMs).
You have real-time access to client CRM data, portfolio holdings, and insurance policies via tools.

Guidelines:
- Always use tools to retrieve live data before answering questions about specific clients or portfolios.
- Be precise with numbers. Always state the as_of_date for portfolio data.
- Highlight risk concerns clearly (e.g., concentration risk, upcoming renewals).
- Format Slack responses concisely: use bullet points, bold (*text*) for key figures, avoid walls of text.
- If a client ID is unknown, use query_clients to look it up first.
- For market impact questions, use market_impact_analyzer and summarize which clients need attention.
- Never fabricate data. If data is unavailable, say so clearly."""

MAX_TOOL_ROUNDS = 10  # prevent infinite loops


def run_claude_loop(user_message: str, conversation_history: list = None) -> str:
    """
    Run the agentic tool call loop.

    Args:
        user_message: The RM's query from Slack.
        conversation_history: Optional prior conversation turns for multi-turn context.

    Returns:
        Final natural language response string from Claude.
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
            # Extract all text blocks as the final answer
            text_blocks = [
                block.text
                for block in response.content
                if hasattr(block, "text") and block.type == "text"
            ]
            return "\n".join(text_blocks).strip() or "I wasn't able to generate a response."

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
            # Continue loop — Claude will process results and may call more tools

        else:
            # Unexpected stop reason (e.g., max_tokens)
            return f"Response was cut short (stop_reason={response.stop_reason}). Please try a more specific question."

    return "I reached the maximum number of tool calls. Please try a more focused question."
