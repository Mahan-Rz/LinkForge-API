# LinkForge-API

**A URL Shortener API built with Django REST Framework**

LinkForge is a backend-focused URL shortening service that allows authenticated users to create and manage shortened URLs, track click activity, and redirect visitors to their original destinations.

The project demonstrates practical backend development using Django REST Framework, PostgreSQL, Redis, Celery, and Docker Compose.

## Features

- **URL shortening:** Generate unique short codes for original URLs.
- **Token authentication:** Authenticate API requests using Django REST Framework tokens.
- **User ownership:** Restrict URL management to the authenticated user's own links.
- **URL management:** Create, retrieve, update, and delete shortened URLs.
- **Redirect handling:** Redirect visitors to original destinations through short URLs.
- **Click analytics:** Track click counts, last-click timestamps, and individual click events.
- **Expiration and activation:** Support expiration dates and inactive URLs.
- **Search and ordering:** Search original URLs and order results by creation time or click count.
- **Pagination:** Paginate URL listings with configurable page sizes.
- **Redis caching:** Cache redirect lookups and invalidate cached entries when URLs are updated or deleted.
- **Background tasks:** Use Celery and Celery Beat for scheduled expiration-related processing.
- **API documentation:** Generate an OpenAPI schema with Swagger UI and ReDoc using `drf-spectacular`.
- **Containerized environment:** Run the application and supporting services with Docker Compose.

## Tech Stack

- Python
- Django
- Django REST Framework
- PostgreSQL
- Redis
- Celery and Celery Beat
- Docker Compose
- drf-spectacular

## API Endpoints

| Method | Endpoint | Description | Authentication |
|---|---|---|---|
| `POST` | `/api/auth/token/` | Obtain an API token | No |
| `GET` | `/api/urls/` | List your shortened URLs | Required |
| `POST` | `/api/urls/` | Create a shortened URL | Required |
| `GET` | `/api/urls/<pk>/` | Retrieve an owned URL | Required |
| `PUT` | `/api/urls/<pk>/` | Update an owned URL | Required |
| `DELETE` | `/api/urls/<pk>/` | Delete an owned URL | Required |
| `GET` | `/<shortened_code>/` | Redirect to the original destination | No |

### Redirect Responses

- `302 Found` — The URL is active and has not expired.
- `404 Not Found` — The shortened code does not exist.
- `410 Gone` — The URL is inactive or has expired.

## API Documentation

Once the application is running, the API documentation is available at:

- **Swagger UI:** `http://localhost:8000/api/docs/`
- **ReDoc:** `http://localhost:8000/api/redoc/`
- **OpenAPI schema:** `http://localhost:8000/api/schema/`

## Authentication

Obtain an API token by sending a `POST` request to `/api/auth/token/` with your Django username and password.

Example request body:

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

For protected endpoints, include the token in the request header:

```http
Authorization: Token YOUR_API_TOKEN
```

The token endpoint and redirect endpoint are public. URL management endpoints require authentication.

## Search, Ordering, and Pagination

The URL listing endpoint supports the following query parameters:

| Parameter | Description | Example |
|---|---|---|
| `search` | Search within original URLs | `?search=example.com` |
| `ordering` | Order by creation time or click count | `?ordering=-click_count` |
| `page` | Select a result page | `?page=2` |
| `page_size` | Set the page size (maximum 100) | `?page_size=20` |

By default, results are ordered by creation time, newest first, with 10 results per page.

## Running the Project

### Prerequisites

- Docker
- Docker Compose

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/Mahan-Rz/LinkForge-API.git
   cd LinkForge-API
   ```

2. Create a `.env` file in the project root and configure the environment variables required by `compose.yaml` and Django settings. These include the PostgreSQL database credentials and the Redis and Celery connection settings where required.

   **Do not commit your `.env` file or expose credentials in the repository.**

3. Build and start the services:

   ```bash
   docker compose up --build
   ```

4. Apply database migrations:

   ```bash
   docker compose exec web python manage.py migrate
   ```

5. Create an administrator account:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

The API should be available at `http://localhost:8000/` when the services start successfully and the web service exposes port `8000`.

### Running Tests

Run the Django test suite inside the web container:

```bash
docker compose exec web python manage.py test
```

The current test suite contains **43 tests**, which have been run successfully.

### Stopping the Services

```bash
docker compose down
```

This stops the containers without deleting the persistent database volume.

## Design Highlights

- **Ownership-based querysets:** Prevent users from accessing or modifying other users' shortened URLs through the management API.
- **Read-only serializer fields:** Protect server-generated short codes, ownership, and analytics fields from client-side modification.
- **Atomic click tracking:** Use Django database transactions and `F()` expressions to make click-count updates safer under concurrent requests.
- **Cache invalidation:** Remove cached redirect entries when the associated URL is updated or deleted.
- **Graceful cache fallback:** Handle Redis cache errors by falling back to database lookup for redirect resolution.
- **API schema generation:** Document API operations and their expected responses using `drf-spectacular`.

## Project Purpose

LinkForge is a portfolio project focused on backend engineering practices, including REST API design, authentication, relational data modeling, caching, background processing, testing, and containerized development.