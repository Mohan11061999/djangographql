from django.test import TestCase
from graphene.test import Client
from config.schema import schema
from library.models import Author, Publisher, Category, Book

class BookQueryTest(TestCase):

    def setUp(self):
        self.client = Client(schema)
        self.author = Author.objects.create(name="Orwell", age=46)
        self.publisher = Publisher.objects.create(name="Penguin")
        self.book = Book.objects.create(
            title="1984", price=15.99, published_year=1949,
            author=self.author, publisher=self.publisher,
        )

    def test_all_books_query(self):
        query = """
            query {
              allBooks {
                title
                author { name }
              }
            }
        """
        response = self.client.execute(query)
        self.assertIsNone(response.get("errors"))
        self.assertEqual(len(response["data"]["allBooks"]), 1)
        self.assertEqual(response["data"]["allBooks"][0]["title"], "1984")

    def test_single_book_query(self):
        query = """
            query GetBook($id: Int!) {
              book(id: $id) {
                title
              }
            }
        """
        response = self.client.execute(query, variables={"id": self.book.id})
        self.assertIsNone(response.get("errors"))
        self.assertEqual(response["data"]["book"]["title"], "1984")

    def test_single_book_query(self):
        query = """
            query GetBook($id: Int!) {
              book(id: $id) {
                title
              }
            }
        """
        response = self.client.execute(query, variables={"id": self.book.id})
        self.assertIsNone(response.get("errors"))
        self.assertEqual(response["data"]["book"]["title"], "1984")
    
    def test_book_not_found(self):
        query = """
            query GetBook($id: Int!) {
              book(id: $id) { title }
            }
        """
        response = self.client.execute(query, variables={"id": 9999})
        self.assertIsNotNone(response.get("errors"))

    def test_filter_books_by_year(self):
        query = """
            query {
              allBooks(publishedYear: 1949) {
                title
              }
            }
        """
        response = self.client.execute(query)
        self.assertEqual(
            len(response["data"]["allBooks"]),
            1
        )