from django.contrib import admin
from django.urls import path
from library.views import book_list_or_create, book_detail

urlpatterns = [
    # Fixed admin path below
    path('admin/', admin.site.urls),
    path('api/books/', book_list_or_create, name='book-list-or-create'),
    path('api/books/<int:book_id>/', book_detail, name='book-detail'),
]