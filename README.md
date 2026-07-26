# Django GraphQL

This repository contains a Django-based web application with GraphQL API endpoints. It demonstrates how to structure a Django project to serve data via GraphQL (typically using Graphene or Strawberry), integrate authentication, and organize apps, schemas, and tests.

## Project overview

- Framework: Django
- GraphQL library: Graphene or Strawberry (configurable in code)
- Database: SQLite by default (can be changed to PostgreSQL/MySQL)
- Authentication: Django auth + token/session support for GraphQL

## Features

- GraphQL API endpoints for core models (CRUD operations)
- Relay/Relay-compatible pagination and mutations (when enabled)
- Query batching and optimized resolvers
- Schema modularization per Django app
- Tests for schema and API behavior

## Repository structure

- manage.py — Django management entrypoint
- project/ — project settings, urls
- apps/ — Django apps containing models, views, schema modules
- requirements.txt — Python dependencies
- README.md — this file

Typical app layout for GraphQL:

- apps/<app>/models.py — Django models
- apps/<app>/schema.py — GraphQL types, queries, mutations
- apps/<app>/tests.py — tests for GraphQL schema and resolvers

## Setup (local development)

1. Create and activate a virtual environment: python -m venv .venv && .venv\Scripts\activate
2. Install dependencies: pip install -r requirements.txt
3. Apply migrations: python manage.py migrate
4. Create a superuser: python manage.py createsuperuser
5. Run the development server: python manage.py runserver

## GraphQL endpoint

By default the GraphQL endpoint is mounted at `/graphql/`. Access the interactive IDE (GraphiQL or Banana Cake Pop for Strawberry) in the browser to explore the schema and run queries/mutations.

Example query:

{
users {
id
username
}
}

## Testing

Run tests with: python manage.py test

## Contributing

1. Fork the repo
2. Create a feature branch
3. Open a pull request with a clear description of changes

## Notes

- Replace the placeholder GraphQL library in requirements.txt and project settings with your chosen implementation (Graphene or Strawberry).
- Configure production settings (ALLOWED_HOSTS, database, static files) before deployment.

## License

Project license information goes here.
