from django.test import TestCase
from graphene.test import Client
from config.schema import schema
from library.tests.factories import AuthorFactory, PublisherFactory, BookFactory


class BookQueryTest(TestCase):

    def setUp(self):
        self.client = Client(schema)
        self.author = AuthorFactory(name="Orwell", age=46)
        self.publisher = PublisherFactory(name="Penguin")
        self.book = BookFactory(
            title="1984",
            price=15.99,
            published_year=1949,
            author=self.author,
            publisher=self.publisher,
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
        self.assertEqual(len(response["data"]["allBooks"]), 1)

    def test_multiple_books_query_count(self):
        # Factory makes it trivial to bulk-create test data
        BookFactory.create_batch(5)
        query = """
            query {
              allBooks { title }
            }
        """
        response = self.client.execute(query)
        # 5 new + 1 from setUp
        self.assertEqual(len(response["data"]["allBooks"]), 6)

       
    def test_all_authors_query(self):
        query = "query { allAuthors { name } }"
        response = self.client.execute(query)
        self.assertIsNone(response.get("errors"))

    def test_all_publishers_query(self):
        query = "query { allPublishers { name } }"
        response = self.client.execute(query)
        self.assertIsNone(response.get("errors"))

    def test_all_categories_query(self):
        query = "query { allCategories { name } }"
        response = self.client.execute(query)
        self.assertIsNone(response.get("errors"))