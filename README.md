# Support Ticket Management API

A RESTful backend application built using **Python, FastAPI, SQLAlchemy, and SQLite** to manage customer support tickets with secure authentication and role-based access control.

## Tech Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0
- **Database:** SQLite
- **Validation:** Pydantic v2
- **Authentication:** JWT (PyJWT)
- **Password Hashing:** Argon2
- **Testing:** Pytest, HTTPX
- **Documentation:** Swagger / OpenAPI
- **Server:** Uvicorn
- **Version Control:** Git, GitHub

## Key Features

- User registration and login with JWT authentication.
- Secure password hashing using Argon2.
- Role-based access control (Admin, Agent, Customer).
- User profile and user management.
- Ticket creation, assignment, updating, and resolution.
- Ticket status and priority management.
- Search, filtering, sorting, and pagination.
- SQLAlchemy ORM for database operations.
- Dependency injection using FastAPI `Depends()`.
- Centralized exception handling and request logging.
- Automated API and unit testing using Pytest and HTTPX.

## Architecture

Implemented a modular, layered architecture with separation of concerns:

- **Routers:** API endpoints and request handling.
- **Schemas:** Request validation and response serialization.
- **Models:** Database entities and relationships.
- **Services:** Business logic.
- **Dependencies:** Database sessions, authentication, and authorization.
- **Core:** Configuration, security, and exception handling.
- **Middleware:** Request logging and execution-time tracking.
- **Tests:** Automated unit and integration tests.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | User registration |
| POST | `/auth/login` | User authentication |
| GET/PUT | `/users/me` | Manage own profile |
| GET/POST | `/users` | User management (Admin) |
| GET/PATCH | `/users/{id}` | Manage users (Admin) |
| POST | `/tickets` | Create ticket |
| GET | `/tickets` | List tickets with filters |
| GET | `/tickets/{id}` | Get ticket details |
| PUT | `/tickets/{id}` | Update ticket |
| PATCH | `/tickets/{id}/status` | Update ticket status |
| PATCH | `/tickets/{id}/assign` | Assign ticket to agent |
| GET | `/tickets/stats` | Ticket statistics (Admin) |
| DELETE | `/tickets/{id}` | Delete ticket (Admin) |

## Getting Started

```bash
# Clone repository
git clone https://github.com/<your-username>/support-ticket-api.git

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
uvicorn app.main:app --reload
```

**Swagger UI:** http://127.0.0.1:8000/docs

## Run Tests

```bash
pytest -v
```

## Concepts Demonstrated

- REST API design and HTTP methods.
- Dependency Injection and middleware.
- Layered architecture and separation of concerns.
- ORM, database relationships, and session management.
- JWT authentication and role-based authorization.
- Request validation and exception handling.
- Search, filtering, sorting, and pagination.
- Unit and integration testing.

## Future Enhancements

- PostgreSQL integration.
- Alembic database migrations.
- Docker containerization.
- Redis caching.
- CI/CD with GitHub Actions.
- Azure cloud deployment.