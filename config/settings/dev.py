from .base import *  # noqa

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow all origins during local development to avoid CORS blocks while
# debugging the frontend integration. Do NOT enable in production.
CORS_ALLOW_ALL_ORIGINS = True

# Trust the local frontend origin for CSRF checks during development.
# Include scheme (http://) as required by Django's CSRF_TRUSTED_ORIGINS.
CSRF_TRUSTED_ORIGINS = ["http://localhost:5174"]


from .base import *  # noqa

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# When running the backend directly (`python manage.py runserver`) instead of
# through `docker-compose`, there's no Redis broker reachable at the `redis`
# hostname — that name only resolves inside the Docker Compose network.
# Running Celery tasks eagerly (in-process, synchronously) removes the need
# for a broker entirely during local development. If you later want to test
# real async/worker behavior, run `docker-compose up redis` and instead set
# REDIS_URL=redis://localhost:6379/0 in your .env, then remove these two lines.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True