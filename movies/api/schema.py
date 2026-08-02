import graphene
from graphene_django import DjangoObjectType
from movies.api.models import Movie


class MovieType(DjangoObjectType):
    class Meta:
        model = Movie

    # custom query fiels
    movie_age = graphene.String()

    def resolve_movie_age (self,info):
        return "Old Movie" if self.year < 2000 else "New Movie"

class Query:
    all_movies = graphene.List(MovieType)
    movie = graphene.Field(MovieType, id=graphene.Int())

    def resolve_all_movies(self, info):
        return Movie.objects.all()

    def resolve_movie(self, info, id):
        if id is not None:
            return Movie.objects.get(id=id)
        return None

class MovieCreateMutation(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        year = graphene.Int(required=True)
    movie = graphene.Field(MovieType)

    def mutate(self, info, title, year):
        movie = Movie.objects.create(title=title, year=year)
        return MovieCreateMutation(movie=movie)

class MovieUpdateMutation(graphene.Mutation):
    class Arguments:
            title = graphene.String()
            year = graphene.Int()
            id = graphene.Int(required=True)
    movie = graphene.Field(MovieType)

    def mutate(self, info, title, year, id):
        movie = Movie.objects.get(pk=id)
        if title is not None:
            movie.title = title
        if year is not None:
            movie.year = year
        movie.save()
        return MovieUpdateMutation(movie=movie)

class MovieDeleteMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
    ok = graphene.Field(MovieType)

    def mutate(self, info, id):
        movie = Movie.objects.get(pk=id)
        movie.delete()
        return MovieDeleteMutation(ok=True)

class Mutation:
    create_movie = MovieCreateMutation.Field()
    update_movie = MovieUpdateMutation.Field()
    delete_movie = MovieDeleteMutation.Field()


# query{
#   allMovies{
#     id
#     title
#     year
#     movieAge
#   }
# }
# query{
#   movie(id:1){
#     id
#     title
#     year
#   }
# }

# mutation{
#   createMovie(title:"The Dark Knight",year:2008){
#     movie{
#       id
#        title
#        year
#     }
#   }
# }

# mutation{
#    updateMovie(id:1,title:"titanic updated",year:1997){
#     movie{
#       id 
#       title
#       year
#     }
#   }
# }

# mutation{
#   deleteMovie(id:2){
#     ok{
#       id
      
#     }
#   }
# }


