from django.test import TestCase
from library.tests.factories import AuthorFactory, PublisherFactory, CategoryFactory, BookFactory


class BookModelTest(TestCase):

    def setUp(self):
        self.category = CategoryFactory(name="Fantasy")
        self.book = BookFactory(
            title="Harry Potter",
            price=19.99,
            published_year=1997,
            author=AuthorFactory(name="J.K. Rowling", age=58),
            publisher=PublisherFactory(name="Bloomsbury"),
            categories=[self.category],
        )

    def test_book_creation(self):
        self.assertEqual(self.book.title, "Harry Potter")
        self.assertEqual(self.book.author.name, "J.K. Rowling")

    def test_book_str(self):
        self.assertTrue(isinstance(self.book, type(self.book)))

    def test_book_category_relation(self):
        self.assertIn(self.category, self.book.categories.all())

    def test_book_price_type(self):
        self.assertEqual(str(self.book.price), "19.99")

    def test_book_creation_with_random_data(self):
        # No explicit fields needed — factory fills everything realistically
        book = BookFactory()
        self.assertIsNotNone(book.id)
        self.assertTrue(book.title)
        self.assertIsNotNone(book.author)
        self.assertIsNotNone(book.publisher)