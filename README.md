# QR-Based Event Registration

A robust event management and registration system that uses QR codes for attendance verification. Built with performance, scalability, and developer experience in mind.

## Features

- **Multi-Event Management**: Create and manage multiple events simultaneously. Admins can toggle event visibility and registration status.
- **Dynamic Profile Completion**: New users are guided through a profile completion flow to collect essential affiliation details (Student ID, University, Organization, etc.).
- **Per-Event Registration**: Users can browse active events and register for them individually.
- **Unique QR Generation**: Secure, per-registration QR codes are generated and emailed to participants.
- **WhatsApp Integration**: Admins can attach WhatsApp group links to events, allowing participants to join communities instantly after registration.
- **Admin Dashboard**: Real-time attendance stats, user management, and event controls.
- **Server-Side Pagination & Search**: Efficiently manage thousands of users with backend-driven pagination and search filters.
- **PDF Attendance Reports**: Export professional attendance reports as PDFs (available globally or per-event).
- **Modern Architecture**: Clean separation of concerns using Repository and Service patterns.
- **Performance Optimized**: Async Supabase integration with persistent connection pooling and request-level performance logging.

## Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+)
- **Database**: [Supabase](https://supabase.com/) (PostgreSQL)
- **Templating**: [Jinja2](https://palletsprojects.com/p/jinja/)
- **UI Framework**: [Bootstrap 5](https://getbootstrap.com/)
- **Package Manager**: [uv](https://docs.astral.sh/uv/)
- **Styling**: Consolidated external CSS with mobile-first responsiveness.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

### Application

1. **Clone the repository**
   ```bash
   git clone https://github.com/fossuok/qr.fossuok.org
   cd qr.fossuok.org
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Configure Environment Variables**
   Copy `.env.example` to `.env` and fill in your Supabase and GitHub OAuth credentials.
   ```bash
   # Windows
   copy .env.example .env

   # Linux/macOS
   cp .env.example .env
   ```

4. **Run the development server**
   ```bash
   python main.py
   ```
   The app will be available at `http://localhost:8000`

### GitHub OAuth Setup

1. Create a "New OAuth App" in [GitHub Developer Settings](https://github.com/settings/developers).
2. Set **Homepage URL** to `http://localhost:8000`.
3. Set **Authorization callback URL** to `http://localhost:8000/auth/callback` (or your production URL).
4. Copy the **Client ID** and **Client Secret** to your `.env` file.

## Project Structure

```text
├── api/             # HTTP route handlers (v1)
│   ├── admin.py     # Admin-only dashboard and management routes
│   ├── auth.py      # GitHub OAuth and session management
│   ├── users.py     # Participant-facing pages and registration
│   └── api.py       # JSON API endpoints (e.g., QR verification)
├── config/          # Supabase client setup (sync & async)
├── middleware/      # Custom middleware (Performance logging)
├── repository/      # Database abstraction layer (CRUD logic)
├── schema/          # Pydantic models (Requests, Responses, Entities)
├── services/        # Business logic (QR, PDF, Mail, Registration)
├── static/          # Static assets (CSS, JS, Icons)
├── templates/       # Jinja2 HTML templates
├── main.py          # App entry point & router registration
└── vercel.json      # Vercel deployment configuration
```

## Endpoints

### Template Endpoints (Web Pages)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home / Login page |
| GET | `/user/complete-profile` | User affiliation form (shown after first login) |
| GET | `/user/events` | Participant dashboard: Register for events & view active QR codes |
| GET | `/admin/dashboard` | Admin dashboard with live attendance stats |
| GET | `/admin/users` | User management (List, Search, Pagination, Promote/Delete) |
| GET | `/admin/events` | Event management (Create, Edit, Toggle, Delete) |
| GET | `/admin/verify` | QR code scanning and attendance verification page |

### Functional Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/export-attendance` | Export global attendance report (PDF) |
| GET | `/admin/export-attendance/{id}` | Export per-event attendance report (PDF) |
| GET | `/user/registrations/{id}/qr` | Download high-quality QR PNG for a specific registration |
| POST | `/api/verify` | JSON API for QR scanning (used by verification page) |

## Workflow

### 1. Participant Experience
- **Login**: Users authenticate via GitHub.
- **Onboarding**: New users must complete their profile details once.
- **Registration**: Users browse the active events list and click "Register".
- **Confirmation**: A unique QR code is displayed on-screen. If a WhatsApp link is provided for the event, a "Join Group" button appears.

### 2. Administrator Controls
- **Role Assignment**: The first admin must be set manually in the Supabase `users` table. Subsequently, admins can promote others via `/admin/users`.
- **Event Lifecycle**: Admins create events and toggle them as "Active". Activating one event automatically deactivates others if configured (standard flow).
- **Attendance**: Admins use the `/admin/verify` page (mobile-friendly) to scan participant QR codes.

## Deployment (Vercel)

1. Connect your GitHub repository to [Vercel](https://vercel.com).
2. Use the **Python** runtime preset.
3. Import your `.env` variables.
4. Update `SUPABASE_GITHUB_CALLBACK_URL` and `GITHUB_REDIRECT_URI` to match your Vercel domain.
5. In Supabase Dashboard, add your Vercel URL to `Authentication` -> `URL Configuration` -> `Site URL`.

---
*Maintained by FOSS Community - University of Kelaniya*
