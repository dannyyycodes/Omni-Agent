"""
Daily Summary Email Scheduler
Sends one email per day with a summary of all workflow runs
"""

import os
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


class DailySummaryEmailer:
    """Sends daily summary emails instead of per-run emails"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
    
    def start(self):
        """Start the daily email scheduler"""
        # Send daily summary at 9 AM UTC
        self.scheduler.add_job(
            func=self.send_daily_summary,
            trigger=CronTrigger(hour=9, minute=0),
            id='daily_summary_email',
            replace_existing=True,
            name="Daily Workflow Summary Email"
        )
        self.scheduler.start()
        print("✅ Daily summary email scheduler started (9 AM UTC daily)")
    
    def send_daily_summary(self):
        """Send daily summary of all workflow runs"""
        try:
            # Get email config
            alert_email = os.environ.get('ALERT_EMAIL')
            smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
            smtp_port = int(os.environ.get('SMTP_PORT', '587'))
            smtp_user = os.environ.get('SMTP_USER')
            smtp_pass = os.environ.get('SMTP_PASS')
            
            if not all([alert_email, smtp_user, smtp_pass]):
                print("⚠️ Email not configured, skipping daily summary")
                return
            
            # Read logs from last 24 hours
            log_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'scheduler_log.json')
            
            if not os.path.exists(log_path):
                print("No logs found, skipping daily summary")
                return
            
            with open(log_path, 'r') as f:
                all_logs = json.load(f)
            
            # Filter last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            recent_logs = [
                log for log in all_logs
                if datetime.fromisoformat(log['timestamp']) > yesterday
            ]
            
            if not recent_logs:
                print("No runs in last 24 hours, skipping email")
                return
            
            # Calculate stats
            total_runs = len(recent_logs)
            successes = [log for log in recent_logs if log['status'] == 'success']
            failures = [log for log in recent_logs if log['status'] != 'success']
            success_rate = (len(successes) / total_runs * 100) if total_runs > 0 else 0
            
            # Build email
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = alert_email
            msg['Subject'] = f"📊 Animal Facts Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            body = f"""
🤖 OMNI Agent - Daily Workflow Report
Date: {datetime.now().strftime('%Y-%m-%d')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SUMMARY (Last 24 Hours)

Total Runs: {total_runs}
✅ Successful: {len(successes)}
❌ Failed: {len(failures)}
Success Rate: {success_rate:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ SUCCESSFUL POSTS ({len(successes)})

"""
            
            for log in successes:
                time = datetime.fromisoformat(log['timestamp']).strftime('%H:%M UTC')
                animal = log.get('animal', 'Unknown')
                body += f"• {time} - {animal}\n"
            
            if failures:
                body += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                body += f"❌ FAILURES ({len(failures)})\n\n"
                for log in failures:
                    time = datetime.fromisoformat(log['timestamp']).strftime('%H:%M UTC')
                    body += f"• {time} - {log.get('status', 'Unknown error')}\n"
            
            body += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 View Details: https://web-production-770b9.up.railway.app/status

Next Report: Tomorrow at 9 AM UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Daily summary email sent to {alert_email}")
            
        except Exception as e:
            print(f"❌ Failed to send daily summary: {str(e)}")


# Global instance
daily_emailer = None

def init_daily_emailer():
    """Initialize and start the daily emailer"""
    global daily_emailer
    if daily_emailer is None:
        daily_emailer = DailySummaryEmailer()
        daily_emailer.start()
    return daily_emailer
