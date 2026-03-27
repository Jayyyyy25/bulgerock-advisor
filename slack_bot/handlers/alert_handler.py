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
ALERT_CHANNEL  = os.environ.get("SLACK_ALERT_CHANNEL", "#wealth-alerts")
ALERT_USER_ID  = os.environ.get("SLACK_ALERT_USER_ID", "")


def post_renewal_alerts(slack_client, days_ahead: int = 30):
    """Post upcoming policy renewals to the alert channel, @mentioning the RM."""
    try:
        raw = query_policies(days_ahead=days_ahead)
        policies = json.loads(raw)
    except Exception as e:
        logger.error(f"Failed to fetch renewal data: {e}")
        return

    if not policies:
        logger.info("No upcoming renewals to alert.")
        return

    # Sort: most urgent first
    policies = sorted(policies, key=lambda p: p["days_until_renewal"])

    mention = f"<@{ALERT_USER_ID}>" if ALERT_USER_ID else "RM"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":bell: Policy Renewal Alert — Next {days_ahead} Days",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{mention} — *{len(policies)} {'policy requires' if len(policies) == 1 else 'policies require'} "
                    f"your attention* in the next {days_ahead} days. Please review and action accordingly."
                ),
            },
        },
        {"type": "divider"},
    ]

    for policy in policies:
        days_left = policy["days_until_renewal"]
        if days_left <= 7:
            urgency = ":red_circle: *URGENT*"
        elif days_left <= 14:
            urgency = ":orange_circle: *Soon*"
        else:
            urgency = ":yellow_circle: Upcoming"

        client_name = policy.get("full_name") or policy.get("client_id", "Unknown")

        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"{urgency}\n"
                        f"*Client:* {client_name} ({policy['client_id']})\n"
                        f"*Policy:* {policy['policy_type']} — _{policy['insurer']}_\n"
                        f"*Coverage:* {policy.get('coverage_type', 'N/A')}"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*Renewal Date:* {policy['renewal_date']}\n"
                        f"*Days Left:* *{days_left}*\n"
                        f"*Annual Premium:* ${policy['premium']:,.0f}\n"
                        f"*Coverage Amount:* ${policy['coverage_amount']:,.0f}"
                    ),
                },
            ],
        })
        blocks.append({"type": "divider"})

    # Footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": ":robot_face: Pocket IA — automated daily renewal check | Contact client to confirm renewal intention before expiry.",
            }
        ],
    })

    try:
        slack_client.chat_postMessage(
            channel=ALERT_CHANNEL,
            text=f"{mention} — {len(policies)} policy renewals in the next {days_ahead} days require your attention.",
            blocks=blocks,
        )
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
