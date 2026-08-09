import graphene
from library.schema import Query, Mutation

schema = graphene.Schema(query=Query, mutation=Mutation)