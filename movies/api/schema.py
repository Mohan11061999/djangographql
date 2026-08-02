import graphene
from graphene_django import DjangoObjectType
from movies.api.models import Movie
import graphql_jwt
from graphql_jwt.decorators import login_required   
from graphene_django.filter.fields import DjangoFilterConnectionField
from graphql_relay import from_global_id 

class MovieType(DjangoObjectType):
    class Meta:
        model = Movie

    # custom query fiels
    movie_age = graphene.String()

    def resolve_movie_age (self,info):
        return "Old Movie" if self.year < 2000 else "New Movie"

class MovieNode(DjangoObjectType):
    class Meta:
        model = Movie
        filter_fields = {
            'title': ['exact', 'icontains', 'istartswith'],
            'year': ['exact'],
        }
        interfaces = (graphene.relay.Node, )

class Query:
    # all_movies = graphene.List(MovieType)
    movie = graphene.Field(MovieType, id=graphene.Int())
    all_movies = DjangoFilterConnectionField(MovieNode)
    # movie = relay.Node.Field(MovieNode)

    @login_required
    def resolve_all_movies(self, info):
        # user = info.context.user
        # if not user.is_authenticated:
        #     raise Exception("Authentication credentials were not provided")
        return Movie.objects.all()

    @login_required
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

# update using relay
class MovieUpdateRelayMutation(graphene.relay.ClientIDMutation):
    class Input:
        title = graphene.String()
        id = graphene.ID(required=True)
    movie = graphene.Field(MovieType)

    @classmethod
    def mutate_and_get_payload(cls, root, info, id,title):
        movie = Movie.objects.get(pk=from_global_id(id)[1])
        if title is not None:
            movie.title = title
        movie.save()
        return MovieUpdateRelayMutation(movie=movie)

class MovieDeleteMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        movie = Movie.objects.get(pk=from_global_id(id)[1])
        movie.delete()
        return MovieDeleteMutation(ok=True)

class Mutation:
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    create_movie = MovieCreateMutation.Field()
    update_movie = MovieUpdateMutation.Field()
    update_movie_relay = MovieUpdateRelayMutation.Field()
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

# mutation{
#   tokenAuth(username:"mohan",password:"mohan@231953"){
#     token
#   }
# }


# mutation{
#   verifyToken(token:"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6Im1vaGFuIiwiZXhwIjoxNzg1NjQ1MjcxLCJvcmlnSWF0IjoxNzg1NjQ0OTcxfQ.DpqttLpMm6yuhIUybU_Q13cpAJ-9-nfKvtTjV9b5pWQ"){
#     payload
#   }
# }

# query{
#   allMovies{
#     edges{
#       node{
#         id
#         title
#         year
#       }
#     }
#   }
# }