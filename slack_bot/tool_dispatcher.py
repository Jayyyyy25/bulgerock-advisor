"""
Maps Claude tool names to their Python implementations.
Any new tool must be registered here AND in agent_tools/tool_registry.py.
"""
import json
from agent_tools.query_clients import query_clients
from agent_tools.query_portfolio import query_portfolio
from agent_tools.query_policies import query_policies
from agent_tools.market_impact_analyzer import market_impact_analyzer
from agent_tools.get_client_full_profile import get_client_full_profile
from agent_tools.query_unmet_clients import query_unmet_clients

TOOL_MAP = {
    "get_client_full_profile": get_client_full_profile,
    "query_unmet_clients":     query_unmet_clients,
    "query_clients":           query_clients,
    "query_portfolio":         query_portfolio,
    "query_policies":          query_policies,
    "market_impact_analyzer":  market_impact_analyzer,
}


def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name with the given inputs. Always returns a JSON string."""
    func = TOOL_MAP.get(tool_name)
    if func is None:
        return json.dumps({"error": f"Unknown tool: '{tool_name}'. Available: {list(TOOL_MAP)}"})
    try:
        return func(**tool_input)
    except TypeError as e:
        return json.dumps({"error": f"Invalid arguments for tool '{tool_name}': {e}"})
    except Exception as e:
        return json.dumps({"error": f"Tool '{tool_name}' raised an exception: {e}"})
