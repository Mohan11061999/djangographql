from django.db import connection
from django.http import JsonResponse


def health_check(request):
    """Used by Docker healthcheck and Nginx upstream monitoring."""
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_ok = False

    status_code = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "degraded", "database": db_ok}, status=status_code)
