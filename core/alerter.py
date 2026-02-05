"""
Telegram Alerter - Sends proactive alerts for failures and important events
"""

import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramAlerter:
    """Sends alerts directly to Telegram"""

    def __init__(self):
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.user_id = os.environ.get('TELEGRAM_ALERT_USER_ID')
        self.enabled = bool(self.bot_token and self.user_id)

        if not self.enabled:
            logger.warning("Telegram alerter disabled - missing TELEGRAM_BOT_TOKEN or TELEGRAM_ALERT_USER_ID")

    def send_alert(self, message: str, silent: bool = False) -> bool:
        """Send an alert message to Telegram"""
        if not self.enabled:
            logger.debug(f"Alert not sent (disabled): {message[:50]}...")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            response = requests.post(url, json={
                "chat_id": self.user_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_notification": silent
            }, timeout=10)

            if response.status_code == 200:
                logger.info(f"Alert sent: {message[:50]}...")
                return True
            else:
                logger.error(f"Failed to send alert: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False

    def alert_task_failed(self, animal: str, error: str, task_id: str = None):
        """Alert when a video task fails"""
        msg = f"""🚨 *VIDEO TASK FAILED*

Animal: {animal}
Error: {error[:200]}
Task ID: {task_id[:12] if task_id else 'N/A'}...
Time: {datetime.utcnow().strftime('%H:%M UTC')}

Reply with "check failures" for details."""

        self.send_alert(msg)

    def alert_task_stuck(self, animal: str, minutes: int, task_id: str = None):
        """Alert when a task is stuck"""
        msg = f"""⚠️ *TASK STUCK*

Animal: {animal}
Stuck for: {minutes} minutes
Task ID: {task_id[:12] if task_id else 'N/A'}...

Reply with "cancel task {task_id}" to abort."""

        self.send_alert(msg)

    def alert_task_completed(self, animal: str, video_url: str = None, posted: bool = False):
        """Alert when a video is completed (optional - can be noisy)"""
        status = "Posted to socials!" if posted else "Video ready (not posted)"
        msg = f"""✅ *VIDEO COMPLETE*

Animal: {animal}
Status: {status}
Time: {datetime.utcnow().strftime('%H:%M UTC')}"""

        self.send_alert(msg, silent=True)  # Silent for success

    def alert_service_error(self, service: str, error: str):
        """Alert when an external service has issues"""
        msg = f"""🔴 *SERVICE ERROR*

Service: {service}
Error: {error[:200]}
Time: {datetime.utcnow().strftime('%H:%M UTC')}

The automation may be affected."""

        self.send_alert(msg)

    def alert_scheduler_run(self, theme: str, animal: str, status: str):
        """Alert on scheduled runs (optional)"""
        icon = "✅" if status == "success" else "❌" if status == "failed" else "🔄"
        msg = f"""{icon} *SCHEDULED RUN*

Theme: {theme}
Animal: {animal}
Status: {status}
Time: {datetime.utcnow().strftime('%H:%M UTC')}"""

        self.send_alert(msg, silent=(status == "success"))


# Global alerter instance
_alerter = None


def get_alerter() -> TelegramAlerter:
    """Get the global alerter instance"""
    global _alerter
    if _alerter is None:
        _alerter = TelegramAlerter()
    return _alerter


def send_alert(message: str) -> bool:
    """Convenience function to send an alert"""
    return get_alerter().send_alert(message)
