"""
Root GraphQL schema, composed from each app's schema.py. Every app owns
its own Query/Mutation classes; this file just multiple-inherits them
together into the single Query/Mutation graphene-django needs.
"""
import graphene

from apps.accounts.schema import AccountsMutation, AccountsQuery
from apps.cart.schema import CartMutation, CartQuery
from apps.catalog.schema import CatalogMutation, CatalogQuery
from apps.core.admin_schema import AdminCustomersQuery, AdminDashboardQuery, AdminMutation
from apps.coupons.schema import CouponsMutation, CouponsQuery
from apps.orders.schema import OrdersMutation, OrdersQuery


class Query(
    AccountsQuery,
    CatalogQuery,
    CartQuery,
    CouponsQuery,
    OrdersQuery,
    AdminDashboardQuery,
    AdminCustomersQuery,
    graphene.ObjectType,
):
    ping = graphene.String()

    def resolve_ping(root, info):
        return "pong"


class Mutation(
    AccountsMutation,
    CatalogMutation,
    CartMutation,
    CouponsMutation,
    OrdersMutation,
    AdminMutation,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)

