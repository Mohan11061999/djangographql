import graphene
from django.db.models import Sum, Count
from django.utils import timezone
from graphene_django import DjangoObjectType

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.core.permissions import admin_required
from apps.inventory.models import ReorderLevel, StockRecord
from apps.orders.models import Order


class LowStockAlertType(graphene.ObjectType):
    product_id = graphene.ID()
    product_name = graphene.String()
    sku = graphene.String()
    available_quantity = graphene.Int()
    threshold = graphene.Int()


class DashboardMetricsType(graphene.ObjectType):
    total_orders = graphene.Int()
    todays_orders = graphene.Int()
    total_revenue = graphene.Decimal()
    todays_revenue = graphene.Decimal()
    total_customers = graphene.Int()
    total_products = graphene.Int()
    pending_shipments = graphene.Int()
    low_stock_alerts = graphene.List(LowStockAlertType)


class AdminDashboardQuery(graphene.ObjectType):
    dashboard_metrics = graphene.Field(DashboardMetricsType)

    @admin_required
    def resolve_dashboard_metrics(root, info):
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        paid_statuses = [
            Order.Status.PAID, Order.Status.PROCESSING, Order.Status.PACKED,
            Order.Status.SHIPPED, Order.Status.OUT_FOR_DELIVERY, Order.Status.DELIVERED,
        ]

        total_orders = Order.objects.count()
        todays_orders = Order.objects.filter(placed_at__gte=today_start).count()

        revenue_agg = Order.objects.filter(status__in=paid_statuses).aggregate(total=Sum("total_amount"))
        total_revenue = revenue_agg["total"] or 0

        todays_revenue_agg = Order.objects.filter(
            status__in=paid_statuses, placed_at__gte=today_start
        ).aggregate(total=Sum("total_amount"))
        todays_revenue = todays_revenue_agg["total"] or 0

        total_customers = User.objects.filter(role=User.Role.CUSTOMER).count()
        total_products = Product.objects.filter(is_active=True).count()
        pending_shipments = Order.objects.filter(status=Order.Status.PACKED).count()

        low_stock = []
        for reorder in ReorderLevel.objects.select_related("product"):
            available = StockRecord.objects.filter(batch__product=reorder.product).aggregate(
                total=Sum("available_quantity")
            )["total"] or 0
            if available <= reorder.threshold:
                low_stock.append(
                    LowStockAlertType(
                        product_id=reorder.product.id,
                        product_name=reorder.product.name,
                        sku=reorder.product.sku,
                        available_quantity=available,
                        threshold=reorder.threshold,
                    )
                )

        return DashboardMetricsType(
            total_orders=total_orders,
            todays_orders=todays_orders,
            total_revenue=total_revenue,
            todays_revenue=todays_revenue,
            total_customers=total_customers,
            total_products=total_products,
            pending_shipments=pending_shipments,
            low_stock_alerts=low_stock,
        )


class CustomerType(DjangoObjectType):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone_number", "is_active", "created_at"]


class AdminCustomersQuery(graphene.ObjectType):
    customers = graphene.List(CustomerType, search=graphene.String())

    @admin_required
    def resolve_customers(root, info, search=None):
        qs = User.objects.filter(role=User.Role.CUSTOMER)
        if search:
            from django.db.models import Q

            qs = qs.filter(Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search))
        return qs.order_by("-created_at")


class DeactivateCustomer(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @admin_required
    def mutate(root, info, user_id):
        updated = User.objects.filter(id=user_id, role=User.Role.CUSTOMER).update(is_active=False)
        if not updated:
            from graphql import GraphQLError

            raise GraphQLError("Customer not found.")
        return DeactivateCustomer(ok=True)


class AdminMutation(graphene.ObjectType):
    deactivate_customer = DeactivateCustomer.Field()
