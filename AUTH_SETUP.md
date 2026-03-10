# Authentication Setup for Nestperts

This guide walks you through setting up Google OAuth authentication for Nestperts, step by step.

## 🎓 What You're Learning

By setting this up, you'll learn about:
- **OAuth 2.0**: Industry-standard protocol for secure authentication
- **API credentials**: How applications securely identify themselves
- **Session management**: How websites remember you're logged in
- **Access control**: Restricting features to authorized users

## 📋 Prerequisites

- A Google account (any Gmail address)
- Access to Google Cloud Console
- 10-15 minutes to complete setup

---

## Part 1: Understanding OAuth 2.0

### What is OAuth?

Think of OAuth like a **hotel check-in system**:

1. **You arrive** → User clicks "Sign in with Google"
2. **Front desk verifies your ID** → Google asks "Do you trust this app?"
3. **You get a key card** → Google gives your app a token
4. **Key card works throughout hotel** → App uses token to verify you

### Why Use Google OAuth?

**Security Benefits:**
- ✅ No passwords to store or manage
- ✅ Google handles security and 2FA
- ✅ Users trust the Google login screen
- ✅ Easy to revoke access if needed

**User Benefits:**
- ✅ One-click sign-in (no registration forms)
- ✅ Don't need another password
- ✅ Use existing Google account

---

## Part 2: Setting Up Google OAuth

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** at the top
3. Click **"New Project"**
4. Project name: `Nestperts Auth` (or anything you like)
5. Click **"Create"**

**Why?** Google organizes OAuth credentials under "projects." This is like creating a folder for your app's settings.

### Step 2: Enable the Google+ API

1. In the search bar, type "Google+ API" and select it
2. Click **"Enable"**

**Why?** This API lets your app request basic user info (name, email, profile picture) from Google.

### Step 3: Configure OAuth Consent Screen

The consent screen is what users see when they click "Sign in with Google."

1. In the sidebar, go to **"APIs & Services" > "OAuth consent screen"**
2. Select **"External"** (allows anyone with a Gmail to sign in)
3. Click **"Create"**

**Fill out the form:**
- **App name**: `Nestperts`
- **User support email**: Your email
- **Developer contact email**: Your email
- Leave other fields empty for now
- Click **"Save and Continue"**

**Scopes page:**
- Click **"Add or Remove Scopes"**
- Select these scopes:
  - `.../auth/userinfo.email` - See your email
  - `.../auth/userinfo.profile` - See your name and picture
  - `openid` - Verify your identity
- Click **"Update"** then **"Save and Continue"**

**Test users page:**
- For now, click **"Save and Continue"** (we'll manage access in Nestperts directly)

**Why scopes matter:** Scopes are like permissions. You're telling Google "I only need email and name, nothing else." This builds trust with users.

### Step 4: Create OAuth Credentials

1. Go to **"APIs & Services" > "Credentials"**
2. Click **"Create Credentials" > "OAuth client ID"**
3. Application type: **"Web application"**
4. Name: `Nestperts Web Client`

**Add authorized URLs:**

Under **"Authorized JavaScript origins"**:
```
http://localhost:5000
```

Under **"Authorized redirect URIs"**:
```
http://localhost:5000/auth/google/callback
```

5. Click **"Create"**

**Important:** A popup shows your credentials. **Copy these values immediately!**

```
Client ID: something.apps.googleusercontent.com
Client Secret: GOCSPX-something
```

**Why redirect URI?** After Google authenticates the user, it needs to know where to send them back. This URL must match exactly what your app requests.

---

## Part 3: Configure Your Application

### Step 1: Update .env File

Open `nexus/.env` and add these lines:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret-here

# Flask Secret Key (for secure sessions)
SECRET_KEY=your-random-secret-key-here
```

**Generate a secure SECRET_KEY:**

Run this in your terminal:
```bash
python3 -c "import os; print(os.urandom(24).hex())"
```

Copy the output and paste it as your `SECRET_KEY`.

**Why SECRET_KEY?** Flask uses this to encrypt session cookies. It's like the master key that encrypts all the "wristbands" your app gives to users.

### Step 2: Install Required Packages

```bash
cd /home/olisemeka.dev/Projects/nexus
uv pip install authlib python-dotenv
```

**What these do:**
- `authlib` - OAuth library that handles the complex handshake with Google
- `python-dotenv` - Loads variables from .env file (keeps secrets out of code)

### Step 3: Run Setup Script

```bash
cd /home/olisemeka.dev/Projects/nexus
python labeller/setup_auth.py
```

This script will:
1. Create the authentication database (`labeller/users.db`)
2. Ask for your admin email
3. Add your email to the approved list
4. Grant you admin privileges

**Example output:**
```
============================================================
Nestperts Authentication Setup
============================================================

✅ Environment variables configured

Initializing authentication database...
✅ Database initialized at labeller/users.db

Let's set up your admin account.
This email will have full access to manage other users.

Enter your Gmail address: your.email@gmail.com
Adding your.email@gmail.com to approved list...
✅ Email approved
Granting admin privileges to your.email@gmail.com...
✅ Admin privileges granted

============================================================
Setup Complete!
============================================================
```

---

## Part 4: Testing the Setup

### Start Nestperts

```bash
cd /home/olisemeka.dev/Projects/nexus
python labeller/app.py --data labeller/nestvision
```

### Test the Login Flow

1. Open http://localhost:5000
2. You should see a login page
3. Click **"Sign in with Google"**
4. Select your Google account
5. Google asks: "Nestperts wants to access your Google Account"
6. Click **"Allow"**
7. You're redirected back to Nestperts, now logged in!

**What just happened?** (The OAuth dance)
1. Your browser → Nestperts: "I want to log in"
2. Nestperts → Google: "Redirect this user to me after they log in"
3. Google → User: "Do you trust Nestperts?" (Consent screen)
4. User → Google: "Yes" (Clicks Allow)
5. Google → Nestperts: "Here's proof they logged in" (Token)
6. Nestperts → Database: "Is this email approved?" (Checks whitelist)
7. Nestperts → User: "Welcome! Here's your session cookie"

---

## Part 5: Managing Users (Admin Panel)

### Access the Admin Panel

Go to: http://localhost:5000/admin

As an admin, you can:

### 1. Add Approved Emails

**What it does:** Only approved emails can log in. This is your whitelist.

**How to:**
1. Type an email in the "Add Approved Email" field
2. Optionally add a note (e.g., "Lab partner" or "Research assistant")
3. Click **"+ Add Email"**

**Important:** They still need to sign in with Google first. This just pre-approves them.

### 2. Remove Approved Emails

**What it does:** Revokes someone's ability to log in (they'll see "Email not approved" message)

**How to:**
1. Find their email in the "Approved Emails" table
2. Click **"Remove"**
3. Confirm the action

**Note:** This doesn't kick them out if they're currently logged in. But they won't be able to log back in.

### 3. View Registered Users

The "Registered Users" table shows:
- **Name & Picture** - From their Google account
- **First Login** - When they first signed in
- **Last Login** - Most recent login
- **Login Count** - How many times they've logged in
- **Status** - Admin or regular user

---

## Part 6: How the Code Works

Now that it's running, let's understand what's happening under the hood.

### Database Structure

Nestperts creates `labeller/users.db` with three tables:

**1. approved_emails** (The Whitelist)
```sql
email           TEXT PRIMARY KEY  -- user@example.com
added_by        TEXT              -- Who approved them
added_at        TEXT              -- When approved
notes           TEXT              -- Optional description
```

**2. users** (Login History)
```sql
email           TEXT PRIMARY KEY  -- user@example.com
name            TEXT              -- "John Doe"
picture         TEXT              -- Google profile pic URL
first_login     TEXT              -- "2024-03-10T14:30:00"
last_login      TEXT              -- "2024-03-10T16:45:00"
login_count     INTEGER           -- Number of logins
```

**3. admin_users** (Superusers)
```sql
email           TEXT PRIMARY KEY  -- admin@example.com
added_at        TEXT              -- When granted admin
```

### The Authentication Flow (Code)

**File: `labeller/auth.py`**

```python
# 1. USER CLICKS "SIGN IN WITH GOOGLE"
@app.route('/auth/google')
def google_login():
    # Redirect to Google's login page
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

# 2. GOOGLE REDIRECTS BACK AFTER LOGIN
@app.route('/auth/google/callback')
def google_callback():
    # Exchange authorization code for user info
    token = google.authorize_access_token()
    user_info = token.get('userinfo')

    email = user_info.get('email')

    # 3. CHECK IF EMAIL IS APPROVED
    if not is_email_approved(email):
        return redirect(url_for('login', not_approved=email))

    # 4. CREATE SESSION
    session['user'] = {
        'email': email,
        'name': user_info.get('name'),
        'picture': user_info.get('picture'),
        'is_admin': is_admin(email)
    }

    return redirect('/')  # Send to dashboard
```

### The Route Protection (Decorators)

**What's a decorator?** Think of it as a bouncer at a club.

```python
# This is a decorator - it "wraps" another function
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user' not in session:
            # Not logged in? Send to login page
            return redirect(url_for('login'))

        # Logged in? Let them through
        return f(*args, **kwargs)

    return decorated_function
```

**Usage:**
```python
@app.route('/secret-page')
@login_required  # ← Bouncer checks credentials here
def secret_page():
    return "Only logged-in users see this!"
```

**What happens:**
1. User requests `/secret-page`
2. `@login_required` runs first (the bouncer)
3. Checks if `session['user']` exists
4. If yes → runs `secret_page()`
5. If no → redirects to `/login`

---

## Part 7: Session Management

### What's a Session?

A **session** is how the website remembers you're logged in across multiple page loads.

**Think of it like a movie theater:**
1. You buy a ticket (log in)
2. Usher gives you a wristband (session cookie)
3. Every room you enter, you show the wristband
4. Theater trusts the wristband (encrypted with SECRET_KEY)
5. When you leave, wristband is removed (logout)

### How Flask Sessions Work

**In Code:**
```python
# LOGIN: Store user info in session
session['user'] = {
    'email': 'user@example.com',
    'name': 'John Doe',
    'is_admin': False
}

# LATER: Check if user is logged in
if 'user' in session:
    current_user = session['user']
    print(f"Hello, {current_user['name']}!")
```

**In Browser:**
When you log in, Flask sends a cookie:
```
Set-Cookie: session=eyJhbGc...encrypted_data...
```

Every request sends this cookie back:
```
Cookie: session=eyJhbGc...encrypted_data...
```

Flask decrypts it using `SECRET_KEY` to get the user data.

**Security:**
- Cookie is encrypted (users can't read or modify it)
- Encrypted with SECRET_KEY (only your server can decrypt)
- HttpOnly flag prevents JavaScript from reading it (XSS protection)

---

## Part 8: Advanced Concepts

### Role-Based Access Control (RBAC)

Nestperts has two roles:

**Admin:**
- Can access `/admin` panel
- Can add/remove approved emails
- Can view all user activity
- Has all normal user permissions

**User:**
- Can annotate images
- Can view projects
- Can use NestDB
- Cannot manage other users

**Implementation:**
```python
@app.route('/admin')
@admin_required  # ← Only admins allowed
def admin_panel():
    # Admin-only code here
    pass

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))

        # Check if user is admin
        if not is_admin(session['user']['email']):
            return jsonify({'error': 'Admin access required'}), 403

        return f(*args, **kwargs)
    return decorated_function
```

### API Endpoint Protection

Regular pages redirect to login. APIs return JSON errors.

```python
@app.route('/api/data')
@api_login_required  # ← Different decorator for APIs
def get_data():
    return jsonify({'data': 'sensitive'})
```

```python
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # Return JSON error instead of redirect
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function
```

**Why different decorators?**
- HTML pages: Redirect to login page (user can log in)
- API endpoints: Return JSON error (frontend handles it)

---

## Part 9: Troubleshooting

### "Redirect URI mismatch" Error

**Problem:** Google shows this error when you try to log in.

**Cause:** The redirect URI in your OAuth request doesn't match what's registered in Google Console.

**Solution:**
1. Check your Google Console → OAuth client
2. Verify "Authorized redirect URIs" contains:
   ```
   http://localhost:5000/auth/google/callback
   ```
3. Make sure there are no typos or trailing slashes
4. Restart Nestperts after changing

### "Email Not Approved" After Login

**Problem:** You log in successfully but see "email not approved" message.

**Solution:**
1. Check if your email is in the approved list:
   ```bash
   sqlite3 labeller/users.db "SELECT * FROM approved_emails;"
   ```
2. If not there, run setup script again:
   ```bash
   python labeller/setup_auth.py
   ```

### Can't Access Admin Panel (403 Error)

**Problem:** You're logged in but `/admin` shows "Admin access required."

**Solution:**
1. Check if you're in the admin list:
   ```bash
   sqlite3 labeller/users.db "SELECT * FROM admin_users;"
   ```
2. Add yourself manually:
   ```bash
   python3 -c "from labeller.auth import add_admin; add_admin('your@email.com')"
   ```

### Session Expires Immediately

**Problem:** You log in but get logged out on next page.

**Cause:** `SECRET_KEY` changed or not set.

**Solution:**
1. Generate a new key:
   ```bash
   python3 -c "import os; print(os.urandom(24).hex())"
   ```
2. Add to `.env`:
   ```
   SECRET_KEY=your-new-key-here
   ```
3. Restart Nestperts

---

## Part 10: Security Best Practices

### ✅ What We're Doing Right

1. **No password storage** - Using Google OAuth (industry standard)
2. **Encrypted sessions** - SECRET_KEY encrypts all session cookies
3. **Whitelist approach** - Only approved emails can access
4. **Role-based access** - Admins have separate permissions
5. **Environment variables** - Secrets never in code (.env file)

### ⚠️ Production Considerations

If you deploy this publicly (not just localhost):

1. **Use HTTPS** - OAuth requires HTTPS in production
   ```python
   app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
   ```

2. **Update redirect URIs** - Change from `localhost` to your domain
   ```
   https://your-domain.com/auth/google/callback
   ```

3. **Stronger SECRET_KEY** - Generate a long random key
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Rate limiting** - Prevent brute-force attacks
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=get_remote_address)
   ```

5. **Database backups** - Backup `users.db` regularly

---

## Summary

You've successfully implemented:
- ✅ Google OAuth 2.0 authentication
- ✅ Session-based user management
- ✅ Email whitelist system
- ✅ Admin panel for user management
- ✅ Route protection with decorators
- ✅ Role-based access control

**Key Files:**
- `labeller/auth.py` - Authentication logic
- `labeller/app.py` - Routes and decorators
- `labeller/users.db` - User database
- `.env` - OAuth credentials (never commit!)

**Next Steps:**
- Add more users through admin panel
- Customize the consent screen in Google Console
- Consider adding email notifications for new users
- Log authentication events for security auditing

---

## Questions or Issues?

Common things to check:
1. Is `.env` loaded? (Check with `print(os.getenv('GOOGLE_CLIENT_ID'))`)
2. Are redirect URIs exact matches?
3. Is the database initialized? (Check for `users.db` file)
4. Is your email in approved_emails table?

Happy authenticating! 🔐
