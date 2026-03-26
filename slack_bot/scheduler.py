"""
Background scheduler for proactive alerts.
Uses APScheduler to run jobs in-process alongside the Slack bot.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .handlers.alert_handler import post_renewal_alerts

logger = logging.getLogger(__name__)


def start_scheduler(slack_client) -> BackgroundScheduler:
    """
    Start the background job scheduler and register all proactive alert jobs.

    Args:
        slack_client: The initialized Slack WebClient from the Bolt app.

    Returns:
        The running BackgroundScheduler instance.
    """
    scheduler = BackgroundScheduler(timezone="UTC")

    # Daily at 08:00 UTC: post policies renewing in next 7 days
    scheduler.add_job(
        post_renewal_alerts,
        trigger=CronTrigger(hour=8, minute=0),
        kwargs={"slack_client": slack_client, "days_ahead": 7},
        id="daily_renewal_alerts",
        replace_existing=True,
        misfire_grace_time=300,  # tolerate up to 5 min delay
    )

    scheduler.start()
    logger.info("Pocket IA scheduler started. Jobs: %s", [j.id for j in scheduler.get_jobs()])
    return scheduler
