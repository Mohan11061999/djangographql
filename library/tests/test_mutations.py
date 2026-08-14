# library/tests/test_mutations.py
from django.test import TestCase
from graphene.test import Client
from config.schema import schema
from library.models import Author, Publisher, Book

class BookMutationTest(TestCase):

    def setUp(self):
        self.client = Client(schema)
        self.author = Author.objects.create(name="Tolkien", age=81)
        self.publisher = Publisher.objects.create(name="HarperCollins")

    def test_create_book(self):
        mutation = """
            mutation CreateBook($input: BookInput!) {
              createBook(input: $input) {
                book { title price }
              }
            }
        """
        variables = {
            "input": {
                "title": "The Hobbit",
                "price": "12.50",
                "publishedYear": 1937,
                "authorId": self.author.id,
                "publisherId": self.publisher.id,
                "categoryIds": [],
            }
        }
        response = self.client.execute(mutation, variables=variables)
        self.assertIsNone(response.get("errors"))
        self.assertEqual(response["data"]["createBook"]["book"]["title"], "The Hobbit")

    def test_update_book(self):
        book = Book.objects.create(
            title="Old Title", price=10, published_year=2000,
            author=self.author, publisher=self.publisher,
        )
        mutation = """
            mutation UpdateBook($id: Int!, $input: BookInput!) {
              updateBook(id: $id, input: $input) {
                book { title }
              }
            }
        """
        variables = {
            "id": book.id,
            "input": {
                "title": "New Title",
                "price": "10.00",
                "publishedYear": 2000,
                "authorId": self.author.id,
                "publisherId": self.publisher.id,
                "categoryIds": [],
            }
        }
        response = self.client.execute(mutation, variables=variables)
        self.assertEqual(response["data"]["updateBook"]["book"]["title"], "New Title")

    def test_delete_book(self):
        book = Book.objects.create(
            title="To Delete", price=5, published_year=2000,
            author=self.author, publisher=self.publisher,
        )
        mutation = """
            mutation DeleteBook($id: Int!) {
              deleteBook(id: $id) { success }
            }
        """
        response = self.client.execute(mutation, variables={"id": book.id})
        self.assertTrue(response["data"]["deleteBook"]["success"])
        self.assertFalse(Book.objects.filter(id=book.id).exists())

    def test_delete_nonexistent_book(self):
        mutation = """
            mutation DeleteBook($id: Int!) {
              deleteBook(id: $id) { success }
            }
        """
        response = self.client.execute(mutation, variables={"id": 9999})
        self.assertIsNotNone(response.get("errors"))

    def test_create_book_invalid_input(self):
        # Missing required field 'title'
        mutation = """
            mutation CreateBook($input: BookInput!) {
              createBook(input: $input) {
                book { title }
              }
            }
        """
        variables = {
            "input": {
                "price": "12.50",
                "publishedYear": 1937,
                "authorId": self.author.id,
                "publisherId": self.publisher.id,
            }
        }
        response = self.client.execute(mutation, variables=variables)
        self.assertIsNotNone(response.get("errors"))