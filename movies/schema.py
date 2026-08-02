import graphene
from graphene_django import DjangoObjectType
import movies.api.schema

class Query(movies.api.schema.Query, graphene.ObjectType):
    pass

class Mutation(movies.api.schema.Mutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)