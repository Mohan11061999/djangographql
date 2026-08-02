from django.test import SimpleTestCase
from movies.api import schema as api_schema


class GrapheneSchemaTests(SimpleTestCase):
    def test_api_schema_is_available(self):
        self.assertTrue(hasattr(api_schema, 'schema'))
