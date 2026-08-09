# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from graphene_django.views import GraphQLView
from config.schema import schema
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("graphql/", GraphQLView.as_view(graphiql=True, schema=schema)),
]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns