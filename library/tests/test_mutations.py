from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from graphene.test import Client
from config.schema import schema
from library.models import Book
from library.tests.factories import AuthorFactory, PublisherFactory, BookFactory


class BookMutationTest(TestCase):

    def setUp(self):
        self.client = Client(schema)
        self.author = AuthorFactory(name="Tolkien", age=81)
        self.publisher = PublisherFactory(name="HarperCollins")
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="tester", password="pass123")

    def _context(self):
        request = self.factory.post("/graphql/")
        request.user = self.user   # authenticated context for protected mutations
        return request

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
        response = self.client.execute(mutation, variables=variables, context=self._context())
        self.assertIsNone(response.get("errors"))
        self.assertEqual(response["data"]["createBook"]["book"]["title"], "The Hobbit")
        
     
    def test_update_nonexistent_book(self):
        mutation = """
            mutation UpdateBook($id: Int!, $input: BookInput!) {
            updateBook(id: $id, input: $input) {
                book { title }
            }
            }
        """
        variables = {
            "id": 9999,
            "input": {
                "title": "Doesn't matter",
                "price": "1.00",
                "publishedYear": 2020,
                "authorId": self.author.id,
                "publisherId": self.publisher.id,
                "categoryIds": [],
            }
        }
        response = self.client.execute(mutation, variables=variables, context=self._context())
        self.assertIsNotNone(response.get("errors"))

    def test_update_book_success(self):
        book = BookFactory(author=self.author, publisher=self.publisher)
        mutation = """
            mutation UpdateBook($id: Int!, $input: BookInput!) {
              updateBook(id: $id, input: $input) {
                book { title price publishedYear }
              }
            }
        """
        variables = {
            "id": book.id,
            "input": {
                "title": "Updated Title",
                "price": "20.00",
                "publishedYear": 2021,
                "authorId": self.author.id,
                "publisherId": self.publisher.id,
                "categoryIds": [],
            }
        }
        response = self.client.execute(mutation, variables=variables, context=self._context())
        self.assertIsNone(response.get("errors"))
        self.assertEqual(response["data"]["updateBook"]["book"]["title"], "Updated Title")

    def test_delete_book_success(self):
        book = BookFactory(author=self.author, publisher=self.publisher)
        mutation = """
            mutation DeleteBook($id: Int!) {
              deleteBook(id: $id) { success }
            }
        """
        response = self.client.execute(mutation, variables={"id": book.id}, context=self._context())
        self.assertIsNone(response.get("errors"))
        self.assertTrue(response["data"]["deleteBook"]["success"])
        self.assertFalse(Book.objects.filter(id=book.id).exists())

    def test_delete_nonexistent_book(self):
        mutation = """
            mutation DeleteBook($id: Int!) {
              deleteBook(id: $id) { success }
            }
        """
        response = self.client.execute(mutation, variables={"id": 9999}, context=self._context())
        self.assertIsNotNone(response.get("errors"))

    def test_create_book_invalid_input(self):
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
                # 'title' deliberately missing
            }
        }
        response = self.client.execute(mutation, variables=variables, context=self._context())
        self.assertIsNotNone(response.get("errors"))