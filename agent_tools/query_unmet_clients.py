"""
Tool: query_unmet_clients
Returns clients who have not been met within the last N days, based on Last_Meeting in Zoho CRM.
"""
import json
from datetime import date, timedelta
from agent_tools.zoho_client import search_contacts


def query_unmet_clients(days: int = 30) -> str:
    """
    Return clients whose last meeting was more than `days` ago, or who have no meeting recorded.

    Args:
        days: Threshold in days (default 30). Also accepts 14 for 2-week check.

    Returns:
        JSON list of clients with their last_meeting_date and days_since_meeting.
    """
    all_clients = search_contacts(limit=50)

    cutoff = date.today() - timedelta(days=days)
    unmet = []

    for c in all_clients:
        last_meeting = c.get("last_meeting_date")
        if not last_meeting:
            unmet.append({**c, "days_since_meeting": None, "reason": "No meeting recorded"})
        else:
            try:
                meeting_date = date.fromisoformat(str(last_meeting))
                days_since = (date.today() - meeting_date).days
                if meeting_date < cutoff:
                    unmet.append({**c, "days_since_meeting": days_since, "reason": f"Last met {days_since} days ago"})
            except ValueError:
                unmet.append({**c, "days_since_meeting": None, "reason": f"Invalid date: {last_meeting}"})

    unmet.sort(key=lambda x: (x["days_since_meeting"] is None, -(x["days_since_meeting"] or 0)))

    return json.dumps({
        "threshold_days": days,
        "cutoff_date": str(cutoff),
        "total_unmet": len(unmet),
        "clients": unmet,
    }, default=str)
