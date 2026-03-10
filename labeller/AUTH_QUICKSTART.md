# Nestperts Authentication - Quick Start

## 🚀 5-Minute Setup

### 1. Install Dependencies
```bash
cd /home/olisemeka.dev/Projects/nexus
uv pip install authlib python-dotenv
```

### 2. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "Nestperts Auth"
3. Enable "Google+ API"
4. Create OAuth consent screen (External, app name: Nestperts)
5. Add scopes: email, profile, openid
6. Create credentials → OAuth client ID → Web application
7. Add redirect URI: `http://localhost:5000/auth/google/callback`
8. Copy Client ID and Client Secret

### 3. Configure Environment

Add to `.env`:
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
SECRET_KEY=$(python3 -c "import os; print(os.urandom(24).hex())")
```

### 4. Run Setup
```bash
python labeller/setup_auth.py
```

Enter your Gmail address when prompted.

### 5. Start Nestperts
```bash
python labeller/app.py --data labeller/nestvision
```

Go to http://localhost:5000 and click "Sign in with Google"

## 📱 Admin Panel

Access: http://localhost:5000/admin

**Add users:**
1. Enter their Gmail address
2. Click "Add Email"
3. They can now sign in

**Remove users:**
1. Find their email in the table
2. Click "Remove"

## 🔐 How It Works

### User Login Flow
```
User clicks "Sign in"
  → Redirects to Google
  → Google asks permission
  → User approves
  → Redirects back with token
  → Check if email approved
  → Create session
  → Redirect to dashboard
```

### Session Management
- Session stored as encrypted cookie
- Encrypted with SECRET_KEY
- Persists across page loads
- Logout clears session

### Access Control
- **Public**: Login page only
- **Authenticated**: All features
- **Admin**: User management + all features

## 📂 Key Files

```
data/
  └── users.db             # User database (created automatically)
labeller/
  ├── auth.py              # Authentication logic
  ├── setup_auth.py        # Setup script
  ├── app.py               # Updated with @login_required
  └── templates/
      ├── login.html       # Login page
      └── admin_panel.html # Admin interface
```

## 🐛 Troubleshooting

**"Redirect URI mismatch"**
→ Check Google Console redirect URI matches exactly:
  `http://localhost:5000/auth/google/callback`

**"Email not approved"**
→ Run: `python labeller/setup_auth.py` and add your email

**"Admin access required"**
→ Check admin_users table:
```bash
sqlite3 labeller/users.db "SELECT * FROM admin_users;"
```

**Session expires immediately**
→ Make sure SECRET_KEY is set in .env

## 📚 Full Documentation

See `AUTH_SETUP.md` for:
- Detailed OAuth explanation
- Security best practices
- Code walkthrough
- Production deployment tips
