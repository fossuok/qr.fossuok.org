# QR-Based Event Registration

This is a sample event registration system that uses QR codes to verify attendance.

## Tech Stack

- **FastAPI** — backend API and HTML page serving
- **SQLAlchemy** + SQLite (prototype) / Supabase Postgres (production)
- **Jinja2** — HTML templates
- **qrcode** — server-side QR code generation

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Setup
### Application

1. Clone the repo
    ```bash
    git clone https://github.com/DasunNethsara-04/test-qr-app.git
    cd qr.fossuok.org
    ```

2. Install dependencies
    ```bash
    uv sync
    ```

3. Copy `.env.example` to `.env` and fill in values
    ```bash
    # Linux/macOS
    cp .env.example .env

    # Windows
    copy .env.example .env
    ```

4. Run the application
    ```bash
    python main.py
    ```
   The app will be available at `http://localhost:8000`

### GitHub (For Login)

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click on "New OAuth App
3. Fill in the following details:
    - Application name: `QR Event Registration`
    - Homepage URL: `http://localhost:8000`
    - Authorization callback URL:
4. Click on "Register application"
5. Copy the "Client ID" and "Client Secret"

## Endpoints

### Pages

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Registration page |
| GET | `/verify` | QR scan & verification page |

### API

| Method | Path | Body | Description |
|--------|------|------|-------------|
| GET | `/health` | — | Server health check |
| POST | `/api/register` | `{ "name": "...", "email": "..." }` | Create user and return QR code as base64 image |
| POST | `/api/verify` | `{ "id": "<uuid>" }` | Verify a scanned QR and return user details |
| GET | `/users/{qr_uuid}/qr` | — | Stream the QR code as a downloadable PNG |

> The interactive API docs are available at `/docs` (Swagger UI) and `/redoc`.

## Project Structure

```
├── config/          # Database connection and session setup
├── models/          # SQLAlchemy ORM models
├── routes/          # HTTP route handlers (thin layer)
├── schemas/         # Pydantic request/response schemas
├── services/        # Business logic (QR generation, user registration, verification)
├── templates/       # Jinja2 HTML templates
├── main.py          # App entry point — lifespan, middleware, router registration
├── pyproject.toml   # Project metadata and dependencies
├── uv.lock          # Dependency lock file
├── vercel.json      # Vercel deployment configuration
└── .env.example     # Template for required environment variables
```