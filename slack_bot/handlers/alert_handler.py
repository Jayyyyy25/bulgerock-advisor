"""
Proactive alert handler for scheduled notifications.
Posts formatted renewal alerts and risk shift summaries to the configured Slack channel.
"""
import os
import json
import logging
from agent_tools.query_policies import query_policies
from agent_tools.market_impact_analyzer import market_impact_analyzer

logger = logging.getLogger(__name__)
ALERT_CHANNEL = os.environ.get("SLACK_ALERT_CHANNEL", "#wealth-alerts")


def post_renewal_alerts(slack_client, days_ahead: int = 7):
    """Post upcoming policy renewals to the alert channel."""
    try:
        raw = query_policies(days_ahead=days_ahead)
        policies = json.loads(raw)
    except Exception as e:
        logger.error(f"Failed to fetch renewal data: {e}")
        return

    if not policies:
        logger.info("No upcoming renewals to alert.")
        return

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":bell: Policy Renewals in the Next {days_ahead} Days",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    for policy in policies:
        urgency = ":red_circle:" if policy["days_until_renewal"] <= 3 else ":yellow_circle:"
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"{urgency} *{policy['full_name']}*\n{policy['policy_type']} — {policy['insurer']}",
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*Renewal:* {policy['renewal_date']}\n"
                        f"*Days Left:* {policy['days_until_renewal']} | "
                        f"*Premium:* ${policy['premium']:,.0f}"
                    ),
                },
            ],
        })

    try:
        slack_client.chat_postMessage(channel=ALERT_CHANNEL, blocks=blocks)
        logger.info(f"Posted {len(policies)} renewal alerts to {ALERT_CHANNEL}")
    except Exception as e:
        logger.error(f"Failed to post renewal alerts: {e}")


def post_market_impact_alert(
    slack_client,
    event_description: str,
    affected_asset_classes: list = None,
    affected_tickers: list = None,
    threshold_pct: float = 20.0,
):
    """Post a market impact analysis to the alert channel."""
    try:
        raw = market_impact_analyzer(
            event_description=event_description,
            affected_asset_classes=affected_asset_classes,
            affected_tickers=affected_tickers,
            exposure_threshold_pct=threshold_pct,
        )
        result = json.loads(raw)
    except Exception as e:
        logger.error(f"Market impact analysis failed: {e}")
        return

    clients = result.get("affected_clients", [])
    if not clients:
        logger.info("No high-exposure clients for this event.")
        return

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":rotating_light: Market Impact Alert: {event_description[:60]}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{len(clients)} client(s)* have >{threshold_pct}% exposure to affected positions.\n"
                    f"Affected classes: {', '.join(affected_asset_classes or [])} | "
                    f"Tickers: {', '.join(affected_tickers or [])}"
                ),
            },
        },
        {"type": "divider"},
    ]

    for c in clients[:10]:  # cap to avoid overly long messages
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*{c['full_name']}* ({c['risk_profile']})",
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        f"Exposure: *{c['exposure_pct']}%* "
                        f"(${c['exposed_value']:,.0f} of ${c['total_aum']:,.0f} AUM)"
                    ),
                },
            ],
        })

    try:
        slack_client.chat_postMessage(channel=ALERT_CHANNEL, blocks=blocks)
        logger.info(f"Posted market impact alert to {ALERT_CHANNEL}")
    except Exception as e:
        logger.error(f"Failed to post market impact alert: {e}")
