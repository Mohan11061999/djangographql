"""
Central RBAC enforcement for GraphQL resolvers/mutations. graphql-jwt
already attaches the authenticated user to info.context.user (or
AnonymousUser); these decorators build role checks on top of that.
"""
from functools import wraps

import graphql_jwt
from graphql import GraphQLError


def login_required(func):
    @wraps(func)
    def wrapper(cls_or_root, info, *args, **kwargs):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")
        return func(cls_or_root, info, *args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(cls_or_root, info, *args, **kwargs):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not user.is_admin:
            raise GraphQLError("Administrator privileges required.")
        return func(cls_or_root, info, *args, **kwargs)

    return wrapper


def verified_email_required(func):
    """Gate checkout on a verified email so order confirmations are deliverable."""

    @wraps(func)
    def wrapper(cls_or_root, info, *args, **kwargs):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required.")
        if not user.is_email_verified:
            raise GraphQLError("Please verify your email address before continuing.")
        return func(cls_or_root, info, *args, **kwargs)

    return wrapper


# Re-exported so app schemas only need to import from apps.core.permissions
jwt_login_required = graphql_jwt.decorators.login_required
