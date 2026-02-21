# QR-Based Event Registration (Prototype)

This is a sample event registration system that uses QR codes to verify attendance.

## Tech Stack
- FastAPI
- SQLAlchemy + SQLite (prototype) / Supabase Postgres (production)
- Jinja2 Templates
- qrcode library

## Requirements
- Python 3.12+
- uv

## Setup
1. Clone the repo
    ```bash
    git clone https://github.com/fossuok/qr.fossuok.org.git
    ```
2. Install dependencies
    ```bash
    uv sync
    ```
3. Copy `.env.example` to `.env` and fill in values
    ```bash
    cp .env.example .env
    ```
4. Run the application
    ```bash
    python main.py
    ```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /register | Registration page |
| GET | /verify | Verification page |
| POST | /api/register | Create user and generate QR |
| POST | /api/verify | Verify a scanned QR |
| GET | /users/{id}/qr | Download QR as PNG |

## Project Structure

```bash
├── config/                  # includes db connection and other configs
├── models/                  # database models
├── routes/                  # api routes
├── schemas/                 # data schemas (pydantic models)
├── templates/               # HTML templates
├── .python-version          # python version
├── main.py                  # main entry point of the FastAPI app
├── pyproject.toml           # project configurations and required packages
├── uv.lock                  # lock file for uv
├── vercel.json              # vercel deployment configurations
└── .env.example             # Template for env variables