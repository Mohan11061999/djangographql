from django.contrib import admin

from library.models import Publisher, Author,Book, Category

admin.site.register([Publisher, Author, Category, Book])
