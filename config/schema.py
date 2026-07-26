import graphene
import library.schema

class Query(library.schema.Query, graphene.ObjectType):
    pass

class Mutation(library.schema.Mutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)
