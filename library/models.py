
from django.db import models

class Publisher(models.Model):
    name = models.CharField(max_length=200)

class Author(models.Model):
    name = models.CharField(max_length=200)
    age = models.IntegerField()

class Category(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    published_year = models.IntegerField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE, related_name="books")
    categories = models.ManyToManyField(Category, related_name="books")