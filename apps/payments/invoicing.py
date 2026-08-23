from django.utils import timezone


def generate_invoice_number(order):
    return f"INV-{order.order_number.replace('ORD-', '')}"


def create_invoice_for_order(order):
    from .models import Invoice

    invoice, _ = Invoice.objects.get_or_create(
        order=order, defaults={"invoice_number": generate_invoice_number(order)}
    )
    # PDF rendering (WeasyPrint/reportlab) is queued as a Celery task in
    # Phase 3 so payment verification never blocks on PDF generation.
    from apps.notifications.tasks import generate_invoice_pdf_task

    generate_invoice_pdf_task.delay(str(invoice.id))
    return invoice
