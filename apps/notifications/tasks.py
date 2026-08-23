"""
Phase 2 note: these tasks are called (via .delay()) from GraphQL mutations
in accounts/orders/payments schemas, so they must exist now with correct
signatures. Phase 3 fills in the actual email templates/PDF rendering;
for now each task sends a plain-text email and logs an EmailLog row so
the system is fully functional end-to-end, just not yet visually polished.
"""
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import EmailLog


def _send_and_log(*, email_type, recipient, subject, body, order=None):
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
        EmailLog.objects.create(
            email_type=email_type, recipient=recipient, subject=subject,
            related_order=order, was_successful=True,
        )
    except Exception as exc:  # noqa: BLE001 - we want to log any send failure
        EmailLog.objects.create(
            email_type=email_type, recipient=recipient, subject=subject,
            related_order=order, was_successful=False, error_message=str(exc)[:500],
        )
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, user_id, token):
    from apps.accounts.models import User

    user = User.objects.get(id=user_id)
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    _send_and_log(
        email_type=EmailLog.EmailType.EMAIL_VERIFICATION,
        recipient=user.email,
        subject="Verify your MedEase account",
        body=f"Hi {user.first_name},\n\nPlease verify your email by visiting:\n{link}\n\nThis link expires in 24 hours.",
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email_task(self, user_id):
    from apps.accounts.models import User

    user = User.objects.get(id=user_id)
    _send_and_log(
        email_type=EmailLog.EmailType.REGISTRATION,
        recipient=user.email,
        subject="Welcome to MedEase",
        body=f"Hi {user.first_name},\n\nThanks for creating a MedEase account.",
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, user_id, token):
    from apps.accounts.models import User

    user = User.objects.get(id=user_id)
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    _send_and_log(
        email_type=EmailLog.EmailType.PASSWORD_RESET,
        recipient=user.email,
        subject="Reset your MedEase password",
        body=f"Hi {user.first_name},\n\nReset your password by visiting:\n{link}\n\nThis link expires in 1 hour. If you didn't request this, you can ignore this email.",
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_task(self, order_id):
    from apps.orders.models import Order

    order = Order.objects.select_related("user").get(id=order_id)
    _send_and_log(
        email_type=EmailLog.EmailType.ORDER_CONFIRMATION,
        recipient=order.user.email,
        subject=f"Order confirmed — {order.order_number}",
        body=f"Hi {order.user.first_name},\n\nYour order {order.order_number} for ₹{order.total_amount} has been confirmed.",
        order=order,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_payment_receipt_task(self, order_id, invoice_id):
    from apps.orders.models import Order
    from apps.payments.models import Invoice

    order = Order.objects.select_related("user").get(id=order_id)
    invoice = Invoice.objects.get(id=invoice_id)
    _send_and_log(
        email_type=EmailLog.EmailType.PAYMENT_RECEIPT,
        recipient=order.user.email,
        subject=f"Payment receipt — {invoice.invoice_number}",
        body=f"Hi {order.user.first_name},\n\nWe received your payment of ₹{order.total_amount} for order {order.order_number}.\nInvoice: {invoice.invoice_number}",
        order=order,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_shipment_tracking_task(self, order_id):
    from apps.orders.models import Order

    order = Order.objects.select_related("user", "shipment").get(id=order_id)
    shipment = order.shipment
    _send_and_log(
        email_type=EmailLog.EmailType.SHIPMENT_TRACKING,
        recipient=order.user.email,
        subject=f"Your order {order.order_number} has shipped",
        body=(
            f"Hi {order.user.first_name},\n\nYour order has shipped via {shipment.courier_name}.\n"
            f"Tracking number: {shipment.tracking_number}\nDispatched: {shipment.dispatch_date}"
        ),
        order=order,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_delivery_confirmation_task(self, order_id):
    from apps.orders.models import Order

    order = Order.objects.select_related("user").get(id=order_id)
    _send_and_log(
        email_type=EmailLog.EmailType.DELIVERY_CONFIRMATION,
        recipient=order.user.email,
        subject=f"Order {order.order_number} delivered",
        body=f"Hi {order.user.first_name},\n\nYour order {order.order_number} has been marked as delivered. We hope you're happy with your purchase!",
        order=order,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_admin_new_order_task(self, order_id):
    from django.conf import settings as dj_settings

    from apps.orders.models import Order

    order = Order.objects.select_related("user").get(id=order_id)
    _send_and_log(
        email_type=EmailLog.EmailType.ORDER_CONFIRMATION,
        recipient=dj_settings.ADMIN_NOTIFICATION_EMAIL,
        subject=f"New paid order — {order.order_number}",
        body=f"New order {order.order_number} from {order.user.email} for ₹{order.total_amount}.",
        order=order,
    )


@shared_task(bind=True, max_retries=2)
def generate_invoice_pdf_task(self, invoice_id):
    """Renders a simple tax-invoice PDF with reportlab and attaches it to the Invoice record."""
    import io

    from django.core.files.base import ContentFile
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    from apps.payments.models import Invoice

    invoice = Invoice.objects.select_related("order__user", "order__shipping_address").get(id=invoice_id)
    order = invoice.order

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "MedEase — Tax Invoice")
    y -= 30

    c.setFont("Helvetica", 10)
    for line in [
        f"Invoice Number: {invoice.invoice_number}",
        f"Order Number: {order.order_number}",
        f"Billed To: {order.user.full_name} <{order.user.email}>",
        f"Shipping Address: {order.shipping_address.line1}, {order.shipping_address.city}, "
        f"{order.shipping_address.state} {order.shipping_address.postal_code}",
    ]:
        c.drawString(50, y, line)
        y -= 15

    y -= 15
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Item")
    c.drawString(300, y, "Qty")
    c.drawString(350, y, "Unit Price")
    c.drawString(450, y, "Line Total")
    y -= 15
    c.setFont("Helvetica", 10)

    for item in order.items.all():
        if y < 100:
            c.showPage()
            y = height - 50
        c.drawString(50, y, item.product_name_snapshot[:40])
        c.drawString(300, y, str(item.quantity))
        c.drawString(350, y, f"Rs. {item.unit_price_snapshot}")
        c.drawString(450, y, f"Rs. {item.line_total}")
        y -= 15

    y -= 15
    c.setFont("Helvetica-Bold", 11)
    for line in [
        f"Subtotal: Rs. {order.subtotal}",
        f"Discount: -Rs. {order.discount_amount}",
        f"Shipping: Rs. {order.shipping_fee}",
        f"Total: Rs. {order.total_amount}",
    ]:
        c.drawString(350, y, line)
        y -= 15

    c.showPage()
    c.save()
    buffer.seek(0)
    invoice.pdf_file.save(f"{invoice.invoice_number}.pdf", ContentFile(buffer.read()), save=True)


@shared_task
def check_low_stock_and_alert_admins():
    """Scheduled via Celery beat (Phase 3) to email admins about low-stock products daily."""
    from django.db.models import Sum

    from apps.inventory.models import ReorderLevel, StockRecord

    for reorder in ReorderLevel.objects.select_related("product"):
        available = StockRecord.objects.filter(batch__product=reorder.product).aggregate(
            total=Sum("available_quantity")
        )["total"] or 0
        if available <= reorder.threshold:
            _send_and_log(
                email_type=EmailLog.EmailType.LOW_STOCK_ALERT,
                recipient=settings.ADMIN_NOTIFICATION_EMAIL,
                subject=f"Low stock: {reorder.product.name}",
                body=f"{reorder.product.name} (SKU {reorder.product.sku}) has {available} units left, at or below the reorder threshold of {reorder.threshold}.",
            )
