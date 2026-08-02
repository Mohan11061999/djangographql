from django.db import models

class Director(models.Model):
    name = models.CharField(max_length=32)
    surname = models.CharField(max_length=32)

    def __str__(self):
        return f"{self.name} {self.surname}"

class Movie(models.Model):
    title = models.CharField(max_length=100)
    year = models.IntegerField(default=2000)
    director = models.ForeignKey(Director, on_delete=models.PROTECT, related_name='movies', default=1)

    def __str__(self):
        return self.title
