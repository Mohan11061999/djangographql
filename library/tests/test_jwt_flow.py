from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from graphene.test import Client
from config.schema import schema
from library.tests.factories import AuthorFactory, PublisherFactory

class JWTFlowTest(TestCase):

    def setUp(self):
        self.client = Client(schema)
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="mohan", password="pass123")
        self.author = AuthorFactory()
        self.publisher = PublisherFactory()

    def _context(self):
        # Every GraphQL call needs a request-like context object
        request = self.factory.post("/graphql/")
        return request

    # STEP 1 — Login and obtain a token
    def test_step1_login_returns_token(self):
        mutation = """
            mutation Login($username: String!, $password: String!) {
              tokenAuth(username: $username, password: $password) {
                token
                payload
              }
            }
        """
        response = self.client.execute(
            mutation,
            variables={"username": "mohan", "password": "pass123"},
            context=self._context(),
        )
        self.assertIsNone(response.get("errors"))
        self.assertIn("token", response["data"]["tokenAuth"])
        self.token = response["data"]["tokenAuth"]["token"]
        return self.token

    # STEP 2 — Login with WRONG password fails
    def test_step2_login_wrong_password_fails(self):
        mutation = """
            mutation Login($username: String!, $password: String!) {
              tokenAuth(username: $username, password: $password) {
                token
              }
            }
        """
        response = self.client.execute(
            mutation,
            variables={"username": "mohan", "password": "wrongpass"},
            context=self._context(),
        )
        self.assertIsNotNone(response.get("errors"))

    # STEP 3 — Protected mutation WITHOUT token fails
    def test_step3_create_book_without_token_fails(self):
        mutation = """
            mutation CreateBook($input: BookInput!) {
              createBook(input: $input) {
                book { title }
              }
            }
        """
        context = self._context()
        context.user = AnonymousUserForTest()  # unauthenticated
        response = self.client.execute(
            mutation,
            variables={
                "input": {
                    "title": "No Auth Book",
                    "price": "9.99",
                    "publishedYear": 2020,
                    "authorId": self.author.id,
                    "publisherId": self.publisher.id,
                }
            },
            context=context,
        )
        self.assertIsNotNone(response.get("errors"))

    # STEP 4 — Protected mutation WITH valid authenticated user succeeds
    def test_step4_create_book_with_authenticated_user_succeeds(self):
        mutation = """
            mutation CreateBook($input: BookInput!) {
              createBook(input: $input) {
                book { title }
              }
            }
        """
        context = self._context()
        context.user = self.user   # simulate an authenticated request

        response = self.client.execute(
            mutation,
            variables={
                "input": {
                    "title": "Authenticated Book",
                    "price": "14.99",
                    "publishedYear": 2023,
                    "authorId": self.author.id,
                    "publisherId": self.publisher.id,
                }
            },
            context=context,
        )
        self.assertIsNone(response.get("errors"))
        self.assertEqual(
            response["data"]["createBook"]["book"]["title"], "Authenticated Book"
        )

    # STEP 5 — Verify token validity
    def test_step5_verify_token(self):
        token = self.test_step1_login_returns_token()
        mutation = """
            mutation VerifyToken($token: String!) {
              verifyToken(token: $token) {
                payload
              }
            }
        """
        response = self.client.execute(
            mutation, variables={"token": token}, context=self._context()
        )
        self.assertIsNone(response.get("errors"))

    # STEP 6 — Refresh an existing token
    def test_step6_refresh_token(self):
        # Login first to get BOTH token and refreshToken
        login_mutation = """
            mutation Login($username: String!, $password: String!) {
            tokenAuth(username: $username, password: $password) {
                token
                refreshToken
            }
            }
        """
        login_response = self.client.execute(
            login_mutation,
            variables={"username": "mohan", "password": "pass123"},
            context=self._context(),
        )
        refresh_token = login_response["data"]["tokenAuth"]["refreshToken"]

        mutation = """
            mutation RefreshToken($refreshToken: String!) {
            refreshToken(refreshToken: $refreshToken) {
                token
                payload
            }
            }
        """
        response = self.client.execute(
            mutation, variables={"refreshToken": refresh_token}, context=self._context()
        )
        self.assertIsNone(response.get("errors"))
        self.assertIn("token", response["data"]["refreshToken"])

    # STEP 7 — "Logout" via revoke_token (requires refresh token flow enabled)
    def test_step7_revoke_token_logs_out(self):
        mutation = """
            mutation Login($username: String!, $password: String!) {
              tokenAuth(username: $username, password: $password) {
                token
                refreshToken
              }
            }
        """
        login_response = self.client.execute(
            mutation,
            variables={"username": "mohan", "password": "pass123"},
            context=self._context(),
        )
        refresh_token = login_response["data"]["tokenAuth"]["refreshToken"]

        revoke_mutation = """
            mutation Revoke($refreshToken: String!) {
              revokeToken(refreshToken: $refreshToken) {
                revoked
              }
            }
        """
        response = self.client.execute(
            revoke_mutation,
            variables={"refreshToken": refresh_token},
            context=self._context(),
        )
        self.assertIsNone(response.get("errors"))
        self.assertIsNotNone(response["data"]["revokeToken"]["revoked"])


class AnonymousUserForTest:
    """Minimal stand-in for django.contrib.auth.models.AnonymousUser in test contexts."""
    is_authenticated = False