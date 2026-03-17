# Nestperts - Expert Annotation Platform

**Port:** 5000
**Authentication:** OAuth (Google) Required
**Tech Stack:** Flask + Turso Cloud DB + OAuth

---

## ⚠️ Important: This is NOT the same as the webapp!

NestScope has **TWO separate applications:**

1. **Public Tools** (port 8501) - No auth, for everyone
   - NestChat, NestVision
   - `/webapp` directory

2. **Expert Tools** (port 5000) - OAuth required, for researchers
   - Nestperts, NestDB, Flood Intelligence
   - `/labeller` directory ← **YOU ARE HERE**

---

## Quick Start

### Run with everything:
```bash
cd /home/olisemeka.dev/Projects/nexus
./run_app.sh
```

### Run labeller only:
```bash
./run_labeller_only.sh
```

### Manual start:
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

## Environment Setup

Required in `/home/olisemeka.dev/Projects/nexus/.env`:

```bash
# OAuth (from Google Cloud Console)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Session security
SECRET_KEY=random-secret-key

# Turso Cloud Database
TURSO_DATABASE_URL=https://users-....turso.io
TURSO_AUTH_TOKEN=eyJ...
```

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
4. After auth, checks if email is approved (Turso DB)
5. If approved, creates session and redirects to projects

---

## Database

Uses **Turso Cloud** (libsql) for:
- User accounts
- Approved emails list
- User permissions
- Project metadata

**Note:** Bird data is in separate SQLite file at `data/bird_data_complete.db`

---

## Permissions System

- **Base Admin:** Defined in `auth.py` by `BASE_ADMIN_EMAIL`
- **Admins:** Can approve users, manage permissions
- **Annotators:** Can annotate projects
- **DB Editors:** Can write to NestDB

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
See `/home/olisemeka.dev/Projects/nexus/LABELLER_TROUBLESHOOT.md`

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
from auth import is_admin, get_current_user

if is_admin():
    # Admin-only code
    pass

user = get_current_user()
print(user['email'])
```

### Add admin-only route:
```python
from auth import admin_required

@app.route('/admin-stuff')
@admin_required  # Only admins can access
def admin_stuff():
    return "Admin page"
```

---

## Links to Public Tools

The labeller includes a "Public Tools" button in the navbar that links to:
- http://localhost:8501 (NestChat, NestVision)

Similarly, the public webapp links to:
- http://localhost:5000 (this app)

They are **completely separate applications** that just link to each other.

---

## Production Deployment

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
- All user auth goes through Turso Cloud DB
- No passwords stored (OAuth only)

---

## Support

If you have issues:
1. Check logs: `tail -f ../logs/nestperts.log`
2. Run tests: `python ../test_labeller.py`
3. See: `../LABELLER_TROUBLESHOOT.md`
