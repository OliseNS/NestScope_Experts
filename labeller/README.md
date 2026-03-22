# Nestperts - Expert Annotation Platform

**Port:** 5000
**Authentication:** OAuth (Google) Required
**Tech Stack:** Flask + local SQLite (auth) + OAuth (Google)

**Repository:** [github.com/OliseNS/nexus_project](https://github.com/OliseNS/nexus_project)

---

## ⚠️ Important: This is NOT the same as the webapp!

NestScope is often deployed as:

1. **Public / analyst UI** (optional, e.g. Streamlit on port **8501** when you ship a `frontend/`)
   - Talks to the FastAPI backend on port 8000

2. **Expert tools** (this app, port **5000**) — OAuth required
   - Nestperts, NestDB, Flood Intelligence
   - `/labeller` directory ← **YOU ARE HERE**

---

## Quick Start

### Run with everything:
```bash
cd /path/to/nexus_project   # your clone of https://github.com/OliseNS/nexus_project
./run_app.sh
```

### Nestperts only (manual):
```bash
cd labeller
python app.py
```

---

## Features

### 🔬 Nestperts (Main Route `/`)
- Project-based annotation workflow
- Swift AI segmentation
- Multi-expert collaboration
- Species labeling
- YOLO/COCO/GeoJSON export

### 🗄️ NestDB (`/nestdb`)
- SQL query editor
- Table explorer
- Data versioning
- Change tracking
- Write access to database

### 🌊 Flood Intelligence (`/flood-intelligence`)
- NOAA real-time water levels
- Flood predictions
- Colony risk assessment

### 📚 Help & Docs (`/help`)
- Documentation portal
- User guides

### 👥 User Management (`/users`)
- Approve/remove users
- Manage permissions
- Admin controls

---

## First-time auth setup (open source)

Nestperts keeps **who may log in** and **roles** in a **local SQLite file** (not Turso). The FastAPI backend uses the same file for display names when attributing NestChat actions to an email.

1. From the **repository root** (with your virtualenv activated), create the auth database and root admin:

   ```bash
   python seed_root_admin.py
   ```

   The script prompts for the root admin email. You can still pass it as an argument if you prefer.

   This creates `data/user_auth.db` (unless you set `AUTH_DB_PATH`), stores the **root admin** email in `app_settings`, and adds that address to the approved list and `admin_users`. The root admin cannot be deleted or demoted by other admins.

2. Add OAuth and session secrets to `.env` at the repo root (see below).

3. Start the app and sign in with Google using the same email you seeded.

**Optional:** `python labeller/setup_auth.py` walks through the same steps interactively.  
**Optional:** `ROOT_ADMIN_EMAIL` in `.env` seeds the root only when **no** `root_email` exists yet (first `init_auth_db()` after a fresh DB). It does not override `seed_root_admin.py`.

**Migrating from Turso:** If you still have `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN`, install `libsql-client` once and run `python scripts/migrate_auth_from_turso.py`, then run `seed_root_admin.py` if you need a protected root row (`app_settings.root_email`).

---

## Environment Setup

Required variables in the repository root `.env`:

```bash
# OAuth (from Google Cloud Console)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Session security (random string)
SECRET_KEY=random-secret-key

# Optional: custom path for Nestperts auth SQLite (default: data/user_auth.db)
# AUTH_DB_PATH=/path/to/user_auth.db

# Optional: bootstrap root on first DB init (see First-time auth setup)
# ROOT_ADMIN_EMAIL=you@example.com
```

You do **not** need Turso or `libsql-client` for normal operation.

---

## OAuth Setup

1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID
3. Add authorized redirect URI:
   - `http://localhost:5000/auth/google/callback`
4. Copy Client ID and Secret to `.env`

---

## Authentication Flow

1. User visits `http://localhost:5000`
2. Redirects to `/login`
3. Redirects to Google OAuth
4. After auth, checks if the email is in the **approved_emails** table (local SQLite)
5. If approved, creates session and redirects to projects

---

## Database

**Auth / users / RBAC:** Local SQLite file (`data/user_auth.db` by default). Tables include `approved_emails`, `users`, `admin_users`, `permissions`, and `app_settings` (root admin). Schema reference: `scripts/user_auth_schema.sql` (mirrors `labeller/auth.init_auth_db`).

**Bird survey data:** Separate SQLite file at `data/bird_data_complete.db` (NestDB, NestChat, etc.).

**Annotation projects:** Files under `labeller/projects/` (runtime).

---

## Permissions System

- **Root admin:** Email stored in `app_settings` (`root_email`), set by `seed_root_admin.py` or `ROOT_ADMIN_EMAIL` on first init. Cannot be removed from the approved list, demoted, or deleted.
- **Admins:** Can approve users and manage permissions (stored in `admin_users` and role `admin`).
- **Annotators:** Can annotate projects
- **DB Editors:** Can write to NestDB (via role permissions)

---

## API Endpoints

### Public (no auth):
- `GET /health` - Health check

### Auth required:
- `GET /` - Projects page
- `GET /login` - Login page
- `GET /auth/google` - OAuth start
- `GET /auth/google/callback` - OAuth callback
- `GET /logout` - Logout
- `GET /users` - User management (admin only)
- `GET /nestdb` - Database manager
- `GET /flood-intelligence` - Flood dashboard
- `GET /help` - Documentation

---

## File Structure

```
labeller/
├── app.py                 # Main Flask application
├── auth.py               # OAuth + permissions system
├── services/             # Service modules
├── templates/            # Jinja2 HTML templates
├── static/              # CSS, JS, assets
├── projects/            # Annotation projects (created at runtime)
├── run_nestperts.sh     # Waitress production start
└── README.md            # This file
```

---

## Troubleshooting

### Port 5000 won't load?
See the main [README.md](https://github.com/OliseNS/nexus_project/blob/main/README.md) and [DOCKER.md](https://github.com/OliseNS/nexus_project/blob/main/DOCKER.md) for deployment and troubleshooting

### Quick checks:
```bash
# Test app import
python ../test_labeller.py

# Check health
curl http://localhost:5000/health

# View logs
tail -f ../logs/nestperts.log
```

---

## Development

### Add new routes:
```python
@app.route('/my-route')
@login_required  # Requires authentication
def my_route():
    return render_template('my_template.html')
```

### Check user permissions:
```python
from labeller.auth import is_admin, get_current_user

user = get_current_user()
if user and is_admin(user['email']):
    # Admin-only code
    pass
```

### Add admin-only route:
```python
from labeller.auth import admin_required

@app.route('/admin-stuff')
@admin_required  # Only admins can access
def admin_stuff():
    return "Admin page"
```

---

## Links to other tools

The navbar may link to a **public** UI (often `http://localhost:8501` if you run Streamlit separately). That UI and Nestperts are separate processes; both typically use the same FastAPI backend on port **8000**.

---

## Production Deployment

**Docker:** See the repository root **`DOCKER.md`** for `docker compose` (API + Nestperts, volumes, TLS, OAuth behind a reverse proxy). **Vision weights (ONNX / PyTorch):** **`docs/VISION_MODELS.md`**.

**Do NOT use Flask development server in production!**

The `run_nestperts.sh` script uses **Waitress** (production WSGI server):
```bash
cd labeller
bash run_nestperts.sh
```

For even more robust production:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## Security Notes

- OAuth tokens are stored in Flask sessions (server-side)
- Session cookie is HTTP-only
- CSRF protection should be added for production
- All user auth data lives in local SQLite (`AUTH_DB_PATH` / default `data/user_auth.db`)
- No passwords stored (OAuth only)

---

## Support

If you have issues:
1. Check logs: `tail -f ../logs/nestperts.log`
2. Run tests: `python ../test_labeller.py`
3. See: `../LABELLER_TROUBLESHOOT.md`
