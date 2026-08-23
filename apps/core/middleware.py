from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from graphql_jwt.shortcuts import get_user_by_token
from graphql_jwt.exceptions import JSONWebTokenError

User = get_user_model()


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    GraphQL requests are authenticated via graphql_jwt's own GRAPHENE
    middleware. This Django-level middleware additionally resolves
    request.user for plain Django views (e.g. the Razorpay webhook,
    health checks) that sit outside the /graphql/ endpoint.
    """

    def process_request(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("JWT "):
            return

        token = auth_header.split(" ", 1)[1].strip()
        try:
            request.user = get_user_by_token(token, request)
        except JSONWebTokenError:
            # Leave request.user as-is (AnonymousUser); the view decides
            # whether authentication was required.
            pass
