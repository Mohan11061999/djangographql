import factory
from library.models import Author, Publisher, Category, Book


class AuthorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Author

    name = factory.Faker("name")
    age = factory.Faker("random_int", min=20, max=90)


class PublisherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Publisher

    name = factory.Faker("company")


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Faker("word")


class BookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Book
        skip_postgeneration_save = True  

    title = factory.Faker("sentence", nb_words=3)
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    published_year = factory.Faker("random_int", min=1950, max=2024)
    author = factory.SubFactory(AuthorFactory)
    publisher = factory.SubFactory(PublisherFactory)

    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        # Allows: BookFactory(categories=[cat1, cat2])
        if not create or not extracted:
            return
        self.categories.set(extracted)