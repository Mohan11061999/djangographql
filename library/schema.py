import graphene
from graphene_django import DjangoObjectType
from .models import Book, Author

# ==========================================
# 1. GRAPHQL OBJECT TYPES (BRIDGES TO ORM)
# ==========================================
class AuthorType(DjangoObjectType):
    class Meta:
        model = Author
        fields = ("id", "name", "bio", "books")

class BookType(DjangoObjectType):
    class Meta:
        model = Book
        fields = ("id", "title", "isbn", "published_date", "author")


# ==========================================
# 2. MUTATIONS (WRITE operations)
# ==========================================

# CREATE BOOK MUTATION
class CreateBook(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        isbn = graphene.String(required=True)
        published_date = graphene.Date(required=True)
        author_id = graphene.Int(required=True)

    book = graphene.Field(BookType)

    def mutate(root, info, title, isbn, published_date, author_id):
        author = Author.objects.get(id=author_id)
        book = Book.objects.create(
            title=title,
            isbn=isbn,
            published_date=published_date,
            author=author
        )
        return CreateBook(book=book)

# UPDATE BOOK MUTATION
class UpdateBook(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        title = graphene.String()
        isbn = graphene.String()

    book = graphene.Field(BookType)

    def mutate(root, info, id, title=None, isbn=None):
        book = Book.objects.get(id=id)
        if title:
            book.title = title
        if isbn:
            book.isbn = isbn
        book.save()
        return UpdateBook(book=book)

# DELETE BOOK MUTATION
class DeleteBook(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)

    success = graphene.Boolean()

    def mutate(root, info, id):
        book = Book.objects.get(id=id)
        book.delete()
        return DeleteBook(success=True)


# ==========================================
# 3. ROOT SCHEMA COMBINATIONS
# ==========================================
class Query(graphene.ObjectType):
    all_books = graphene.List(BookType)
    book_by_id = graphene.Field(BookType, id=graphene.Int(required=True))

    def resolve_all_books(root, info):
        return Book.objects.select_related('author').all()

    def resolve_book_by_id(root, info, id):
        try:
            return Book.objects.get(id=id)
        except Book.DoesNotExist:
            return None

class Mutation(graphene.ObjectType):
    create_book = CreateBook.Field()
    update_book = UpdateBook.Field()
    delete_book = DeleteBook.Field()
