import graphene
from graphene_django import DjangoObjectType
from .models import Publisher, Author, Category, Book
from graphene_django.debug import DjangoDebug


class PublisherType(DjangoObjectType):
    class Meta:
        model = Publisher
        fields = "__all__"


class AuthorType(DjangoObjectType):
    class Meta:
        model = Author
        fields = "__all__"


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = "__all__"


class BookType(DjangoObjectType):
    class Meta:
        model = Book
        fields = "__all__"

class Query(graphene.ObjectType):
    debug = graphene.Field(DjangoDebug, name="_debug")
    all_books = graphene.List(
        BookType,
        published_year=graphene.Int()
    )
    book = graphene.Field(BookType, id=graphene.Int(required=True))

    all_authors = graphene.List(AuthorType)
    all_publishers = graphene.List(PublisherType)
    all_categories = graphene.List(CategoryType)

    def resolve_all_books(root, info, published_year=None):
        queryset = (
            Book.objects
            .select_related("author", "publisher")
            .prefetch_related("categories")
        )

        if published_year is not None:
            queryset = queryset.filter(
                published_year=published_year
            )

        return queryset

    def resolve_book(root, info, id):
        return (
            Book.objects
            .select_related("author", "publisher")
            .prefetch_related("categories")
            .get(pk=id)
        )

    def resolve_all_authors(root, info):
        return Author.objects.prefetch_related("books")

    def resolve_all_publishers(root, info):
        return Publisher.objects.prefetch_related("books")

    def resolve_all_categories(root, info):
        return Category.objects.prefetch_related("books")

class BookInput(graphene.InputObjectType):
    title = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    published_year = graphene.Int(required=True)
    author_id = graphene.Int(required=True)
    publisher_id = graphene.Int(required=True)
    category_ids = graphene.List(graphene.Int)


class CreateBook(graphene.Mutation):
    class Arguments:
        input = BookInput(required=True)

    book = graphene.Field(BookType)

    def mutate(root, info, input):
        book = Book.objects.create(
            title=input.title,
            price=input.price,
            published_year=input.published_year,
            author_id=input.author_id,
            publisher_id=input.publisher_id,
        )
        if input.category_ids:
            book.categories.set(input.category_ids)
        return CreateBook(book=book)
class UpdateBook(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        input = BookInput(required=True)

    book = graphene.Field(BookType)

    def mutate(root, info, id, input):
        try:
            book = Book.objects.get(pk=id)
        except Book.DoesNotExist:
            raise Exception("Book not found")

        book.title = input.title
        book.price = input.price
        book.published_year = input.published_year
        book.author_id = input.author_id
        book.publisher_id = input.publisher_id
        book.save()

        if input.category_ids is not None:
            book.categories.set(input.category_ids)

        return UpdateBook(book=book)


class DeleteBook(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)

    success = graphene.Boolean()

    def mutate(root, info, id):
        try:
            book = Book.objects.get(pk=id)
        except Book.DoesNotExist:
            raise Exception("Book not found")

        book.delete()
        return DeleteBook(success=True)


class Mutation(graphene.ObjectType):
    create_book = CreateBook.Field()
    update_book = UpdateBook.Field()
    delete_book = DeleteBook.Field()



# query {
#   allBooks {
#     id
#     title
#     price
#     publishedYear
#     author {
#       id
#       name
#       age
#     }
#     publisher {
#       id
#       name
#     }
#     categories {
#       id
#       name
#     }
#   }
# }

# query {
#   book(id: 1) {
#     id
#     title
#     price
#     author { name }
#     publisher { name }
#     categories { name }
#   }
# }

# query {
#   allAuthors {
#     id
#     name
#     age
#     books {
#       id
#       title
#       price
#     }
#   }
# }

# query {
#   allPublishers {
#     id
#     name
#     books {
#       id
#       title
#     }
#   }
# }

# query {
#   allCategories {
#     id
#     name
#     books {
#       id
#       title
#     }
#   }
# }

# query {
#   allBooks {
#     title
#     price
#   }
# }

# query {
#   books: allBooks {
#     title
#   }
#   authors: allAuthors {
#     name
#   }
#   publishers: allPublishers {
#     name
#   }
#   categories: allCategories {
#     name
#   }
# }


# mutation {
#   createBook(input: {
#     title: "Django for Beginners"
#     price: "29.99"
#     publishedYear: 2024
#     authorId: 1
#     publisherId: 1
#     categoryIds: [1, 2]
#   }) {
#     book {
#       id
#       title
#       author { name }
#       categories { name }
#     }
#   }
# }


# mutation {
#   updateBook(id: 1, input: {
#     title: "Django for Beginners (2nd Edition)"
#     price: "34.99"
#     publishedYear: 2025
#     authorId: 1
#     publisherId: 1
#     categoryIds: [1, 3]
#   }) {
#     book {
#       id
#       title
#       price
#       publishedYear
#     }
#   }
# }


# mutation {
#   deleteBook(id: 1) {
#     success
#   }
# }

# query GetBook($id: Int!) {
#   book(id: $id) {
#     title
#     author { name }
#   }
# }
# variables:
# { "id": 1 }

# mutation CreateNewBook($input: BookInput!) {
#   createBook(input: $input) {
#     book { id title }
#   }
# }

# variables:
# {
#   "input": {
#     "title": "New Book",
#     "price": "19.99",
#     "publishedYear": 2024,
#     "authorId": 1,
#     "publisherId": 1,
#     "categoryIds": [1, 2]
#   }
# }