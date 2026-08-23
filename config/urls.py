from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_file_upload.django import FileUploadGraphQLView

from apps.core.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    # FileUploadGraphQLView is a drop-in superset of graphene_django's
    # GraphQLView that additionally accepts multipart requests for mutations
    # like UploadProductImage (see apps.catalog.schema).
    #
    # csrf_exempt: this API authenticates via JWT bearer tokens (Authorization
    # header), not Django session cookies, so it isn't vulnerable to CSRF —
    # but Django's CsrfViewMiddleware still checks every unsafe-method
    # request (which is all of them; GraphQL always POSTs) unless the view
    # is explicitly exempted. Without this, every single query and mutation
    # is rejected with a 403 before it ever reaches a resolver.
    path("graphql/", csrf_exempt(FileUploadGraphQLView.as_view(graphiql=settings.DEBUG))),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# NOTE: in production, /media/ is served directly by Nginx (see nginx/nginx.conf),
# not by Django, for performance reasons.
