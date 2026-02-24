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

### Template Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home / Login page |
| GET | `/user/registration-success` | Registration success page with QR code |
| GET | `/admin/dashboard` | Admin dashboard with event stats |
| GET | `/admin/verify` | QR code scanning and verification page |

> Interactive API documentation is available at `/docs` (Swagger UI) and `/redoc`.



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

## Deployment Guide - Vercel
To deploy this application on Vercel ( **Hope you alreday have a account that already connected to GitHub** ), follow these steps:

### 1. Supabase Setup
Since the Supabase project already created, you have to add the following environment variables to the `.env` file.
1. Go to Supabase with your account (FOSSUOK account)
2. Select the project name `qr.fossuok.org`
3. Go to `Settings` -> `Project Settings` -> `API Keys` -> `Legacy anon, service_role API keys`
4. Copy the `anon` and `service_role` keys and paste them in the `.env` file
5. Without leaving the page go down to `Data API`
6. Copy the `Project URL` and paste it in the `.env` file

    `Note: All the required tables are already created in the database`

### 2. Vercel Setup
1. Go to [Vercel](https://vercel.com)
2. Click on "New Project"
3. Select the repository `qr.fossuok.org`
4. Make sure the `Application Preset` is set to Python
5. Click on the `Environment Variables` dropdown menu and add the variables in the `.env` file or just simply click on `Import .env` file and upload the `.env` file.
6. Before clicking on Deploy, make sure all the Environment Variables are added and correct.
7. Click on Deploy and wait for the deployment to finish.
8. After the deployement, you have to copy the URL of the deployed application.
9. Go back to your `Supabase` project and go to `Authentication` -> `URL Configuration`.
10. Pase the URL of the deployed application in the `Site URL` field.
11. Go back to your Vercel project and go to `Settings` -> `Environment Variables`.
12. Find the `SUPABASE_GITHUB_CALLBACK_URL` variable and update it with the URL with the following format:
    ```bash
    https://<your-vercel-url>/auth/callback
    ```

13. Click on save and it will prompt you to redeploy the application.
14. Click on redeploy and wait for the deployment to finish.
15. App is ready!

## Important Note - For login

### 1. Participant Registration
- **How to register**: Users simply log in using their GitHub account.
- **Workflow**: Upon first login, the system automatically creates a profile and registers the user for the currently **Active Event**.
- **QR Code**: A unique QR code is generated and automatically sent to the user's registered GitHub email address. It is also displayed on the registration success page.

### 2. Admin Access
- **How to login**: Admins also use the GitHub login flow.
- **Granting Admin Rights**: Currently, there is no UI to promote a user to Admin. You must manually update the `role` column to `admin` in the Supabase `users` table for that specific user.
- **Admin Dashboard**: Once the role is updated, the user will be redirected to the Admin Dashboard (`/admin/dashboard`) upon login.

### 3. Event Management
- **Active Event**: Registration only works if there is an event in the `events` table with `is_active` set to `true`.
- **Management**: Currently, events must be created and managed directly via the Supabase dashboard.

### 4. TODO: Missing Features / Future Improvements
- **User Role Management UI**: No interface to manage user roles within the app.
- **Event Management UI**: No interface to create or edit events.
- **QR Recovery**: Users can only see their QR code during registration or in their email. There is no "My Profile" page yet.
