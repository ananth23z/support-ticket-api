# Support Ticket Management API

A beginner-friendly, production-style REST API built with **FastAPI**, **SQLAlchemy**, **SQLite**, **JWT** and **Argon2**.
Customers raise tickets, agents resolve them, and admins manage users and assign work.

Every file is heavily commented, including comparisons to **ASP.NET Core** concepts.
See `Support_Ticket_API_Guide.pdf` for a full walkthrough.

## Quick start

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
uvicorn app.main:app --reload

# 4. Open Swagger UI
#    http://127.0.0.1:8000/docs
```

A default admin is created on first start: **admin@example.com / Admin@123**
(click **Authorize** in Swagger, put the email in the *username* box).

## Run the tests

```bash
pytest -v
```

## Project structure

```
app/
├── main.py                  # entry point: wires everything together (like Program.cs)
├── dependencies.py          # DI: get_db, get_current_user, require_roles
├── core/
│   ├── config.py            # settings (like appsettings.json)
│   ├── database.py          # engine, session, Base, get_db
│   ├── security.py          # Argon2 hashing + JWT create/decode
│   ├── exceptions.py        # custom errors + centralized handlers
│   └── logging_config.py    # logging setup
├── models/                  # SQLAlchemy tables (entities)
├── schemas/                 # Pydantic request/response models (DTOs)
├── services/                # business logic
├── routers/                 # API endpoints (controllers)
└── middleware/              # request logging + timing
tests/                       # pytest API + unit tests
```

## Endpoints

| Method | Path | Who | Purpose |
|---|---|---|---|
| POST | `/auth/register` | public | Register a customer |
| POST | `/auth/login` | public | Get a JWT token |
| GET/PUT | `/users/me` | any user | View / update own profile |
| GET/POST | `/users` | admin | List / create users (create agents here) |
| GET/PATCH | `/users/{id}` | admin | View / change role or deactivate |
| POST | `/tickets` | customer | Create a ticket |
| GET | `/tickets` | any user | List visible tickets (search, filter, sort, paginate) |
| GET | `/tickets/stats` | admin | Ticket statistics |
| GET | `/tickets/{id}` | owner / assigned agent / admin | View a ticket |
| PUT | `/tickets/{id}` | owner (while open) / admin | Edit title, description, priority |
| PATCH | `/tickets/{id}/status` | assigned agent / admin | Change status |
| PATCH | `/tickets/{id}/assign` | admin | Assign to an agent |
| DELETE | `/tickets/{id}` | admin | Delete |

Example list query: `/tickets?search=login&status=open&priority=high&sort_by=priority&order=desc&page=1&size=10`

## Uploading to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Support Ticket Management API"
git branch -M main
git remote add origin https://github.com/<your-username>/support-ticket-api.git
git push -u origin main
```
