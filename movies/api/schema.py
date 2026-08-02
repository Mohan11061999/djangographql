import graphene
from graphene_django import DjangoObjectType
from movies.api.models import Movie


class MovieType(DjangoObjectType):
    class Meta:
        model = Movie

class Query:
    all_movies = graphene.List(MovieType)

    def resolve_all_movies(self, info):
        return Movie.objects.all()

