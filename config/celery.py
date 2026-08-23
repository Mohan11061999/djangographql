import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("medease")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-low-stock-daily": {
        "task": "apps.notifications.tasks.check_low_stock_and_alert_admins",
        "schedule": crontab(hour=8, minute=0),  # 8 AM IST daily
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
