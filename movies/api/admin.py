from django.contrib import admin

from movies.api.models import Movie, Director

# Register your models here.
admin.site.register(Movie)
admin.site.register(Director)