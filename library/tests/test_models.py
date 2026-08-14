from django.test import TestCase
from library.models import Author, Publisher, Category, Book

class BookModelTest(TestCase):

    def setUp(self):
        # Runs before EVERY test method — fresh data each time
        self.author = Author.objects.create(name="J.K. Rowling", age=58)
        self.publisher = Publisher.objects.create(name="Bloomsbury")
        self.category = Category.objects.create(name="Fantasy")
        self.book = Book.objects.create(
            title="Harry Potter",
            price=19.99,
            published_year=1997,
            author=self.author,
            publisher=self.publisher,
        )
        self.book.categories.add(self.category)

    def tearDown(self):
        # Runs after EVERY test — usually not needed, Django rolls back the test DB automatically
        pass

    def test_book_creation(self):
        self.assertEqual(self.book.title, "Harry Potter")
        self.assertEqual(self.book.author.name, "J.K. Rowling")

    def test_book_str(self):
        self.assertTrue(isinstance(self.book, Book))

    def test_book_category_relation(self):
        self.assertIn(self.category, self.book.categories.all())

    def test_book_price_type(self):
        self.assertEqual(str(self.book.price), "19.99")