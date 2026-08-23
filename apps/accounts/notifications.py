"""
Thin wrappers so schema/mutation code never imports Celery tasks directly
(keeps schema.py importable even before Phase 3's tasks.py exists, and
keeps task-queueing logic in one place).
"""


def send_verification_email(user, token):
    from apps.notifications.tasks import send_verification_email_task

    send_verification_email_task.delay(str(user.id), str(token))


def send_password_reset_email(user, token):
    from apps.notifications.tasks import send_password_reset_email_task

    send_password_reset_email_task.delay(str(user.id), str(token))


def send_welcome_email(user):
    from apps.notifications.tasks import send_welcome_email_task

    send_welcome_email_task.delay(str(user.id))
