# Role-Based Access Control (RBAC) in Nestperts

## 🎉 What Was Implemented

A comprehensive permission system that integrates authentication with your workflow:
- ✅ **3 User Roles** with different capabilities
- ✅ **Granular Permissions** for annotation, DB editing, and user management
- ✅ **Admin Panel** for managing user roles
- ✅ **Task Assignment** restricted to logged-in users with permissions
- ✅ **Logout Buttons** throughout the interface
- ✅ **Health Check** for monitoring (works without authentication)

---

## 🔐 Permission Levels Explained

### 1. Admin
**Full Access - Can do everything**
- ✅ Manage users (add/remove emails, change roles)
- ✅ Edit database via NestDB
- ✅ Annotate images
- ✅ View all content

**Who should be Admin:**
- You (the project owner)
- Trusted team leads
- Database administrators

### 2. Annotator
**Can annotate & view, but cannot edit DB**
- ✅ Annotate images with bounding boxes
- ✅ Assign species to detections
- ✅ View database (read-only)
- ❌ Cannot edit database records
- ❌ Cannot manage users

**Who should be Annotator:**
- Lab members doing annotation work
- Research assistants
- Student annotators
- Most of your team

### 3. Viewer
**Read-only access**
- ✅ View images
- ✅ View database (read-only)
- ❌ Cannot annotate
- ❌ Cannot edit database
- ❌ Cannot manage users

**Who should be Viewer:**
- External collaborators
- Observers
- People reviewing data only

---

## 📊 Database Schema

### New Tables Added

**`permissions` table:**
```sql
role            can_annotate  can_edit_db  can_manage_users
admin           1            1            1
annotator       1            0            0
viewer          0            0            0
```

**`users` table (updated):**
- Added `role` column (default: 'viewer')
- Auto-assigned to 'admin' if in admin_users table

---

## 🎯 How It Works

### Login Flow with Roles

```
1. User signs in with Google
   ↓
2. System checks approved_emails list
   ↓
3. User record created/updated with default role
   ↓
4. Permissions loaded from role
   ↓
5. Session stores: email, name, picture, role, permissions
   ↓
6. User redirected to dashboard
```

### Permission Checking

Every protected route now checks permissions:

```python
@app.route('/api/save_annotations')
@api_annotator_required  # Only annotators & admins
def save_annotations():
    # Annotation code
```

```python
@app.route('/nestdb/edit')
@api_db_editor_required  # Only admins
def edit_db():
    # DB edit code
```

---

## 🎮 Admin Panel Usage

### Accessing the Admin Panel

**URL:** http://localhost:5000/admin

**Who can access:** Only users with Admin role

### Features

1. **Dashboard Stats:**
   - Approved emails count
   - Registered users count
   - Total logins
   - Users by role (admins, annotators, viewers)

2. **Approve New Users:**
   - Enter email address
   - Add optional notes
   - Click "Add Email"
   - User can now sign in

3. **Manage User Roles:**
   - View all registered users
   - See their current role
   - Change role with dropdown (auto-saves)
   - See permissions for each role
   - Cannot change your own role (safety feature)

4. **Remove Access:**
   - Find user in approved emails list
   - Click "Remove"
   - User can no longer log in

---

## 🚀 Setting Up Users

### Step 1: You're Already Admin

Your email (`olisemekanmarkwe@gmail.com`) is already set as Admin ✅

### Step 2: Add Team Members

1. Go to http://localhost:5000/admin
2. Enter their Gmail address in "Add Approved Email"
3. Add a note (e.g., "Lab member - annotator")
4. Click "Add Email"

### Step 3: They Sign In

1. They visit http://localhost:5000
2. Click "Sign in with Google"
3. Sign in with the email you approved
4. **Default role:** Viewer (safest)

### Step 4: Assign Appropriate Role

1. In admin panel, find their name in "Registered Users & Roles"
2. Use the dropdown to change their role:
   - **Admin** - Full access
   - **Annotator** - For most team members
   - **Viewer** - For read-only access
3. Role updates immediately (page refresh for them)

---

## 👥 Task Assignment (Updated)

### Old Behavior
- Manual usernames typed in
- Anyone could be assigned
- No authentication check

### New Behavior
- **Only logged-in users** appear in assignment list
- **Only annotators & admins** can be assigned tasks
- **Viewers** don't appear (they can't annotate)
- Shows user's real name, email, and profile picture

### API Change

**Endpoint:** `GET /api/users`

**Before:**
```json
{
  "users": [
    {"name": "john_doe"},
    {"name": "jane_smith"}
  ]
}
```

**After:**
```json
{
  "users": [
    {
      "name": "John Doe",
      "email": "john@example.com",
      "picture": "https://...",
      "role": "annotator",
      "can_annotate": true
    }
  ]
}
```

---

## 🎨 UI Updates

### 1. Logout Button

**Where:** Top-right corner of every page

**What it shows:**
- Your profile picture
- Your name
- Your role
- Logout button (red)

**Location:** All pages using base.html template:
- Projects dashboard
- Users page
- NestDB
- Help page
- Editor

### 2. Admin Link

**Where:** Main navigation bar

**Visible to:** Admins only

**Shows:** "Admin" link next to Help

### 3. Role Badges

**In admin panel:**
- 🟡 Admin (yellow badge)
- 🔵 Annotator (blue badge)
- ⚪ Viewer (gray badge)

**Shows permissions:**
- Green dots = Has permission
- Gray dots = No permission

---

## 🔒 Protected Routes

### Annotation Routes (Annotator or Admin Required)

```
POST /api/save_annotations
POST /api/sam_segment
POST /api/classify_crop
```

**Error if viewer tries:**
```json
{
  "error": "Annotator permission required"
}
```

### Database Edit Routes (Admin Required)

All NestDB edit operations require admin role.

**Error if non-admin tries:**
```json
{
  "error": "Database edit permission required"
}
```

### Admin Routes (Admin Required)

```
GET  /admin
POST /admin/add-email
POST /admin/remove-email
POST /admin/update-role
```

---

## ❤️ Health Check (Public)

**Endpoint:** `GET /health`

**No authentication required** - allows monitoring tools to check service

**Response:**
```json
{
  "status": "healthy",
  "service": "nestperts",
  "port": 5000,
  "users": 3,
  "authenticated": false
}
```

**Why it's public:**
- System health dashboard needs to check all services
- Can't require login for monitoring
- Only returns basic stats (no sensitive data)

---

## 🧪 Testing the System

### Test 1: Admin Access

1. Log in as `olisemekanmarkwe@gmail.com`
2. ✅ Should see "Admin" link in nav
3. ✅ Click Admin → Should see admin panel
4. ✅ Can change user roles
5. ✅ Can annotate images
6. ✅ Can edit NestDB

### Test 2: Add Annotator

1. In admin panel, approve a Gmail address
2. Have that person log in
3. In admin panel, change their role to "Annotator"
4. As them:
   - ✅ Can annotate images
   - ✅ Can view NestDB (read-only)
   - ❌ Cannot access /admin
   - ❌ Cannot edit NestDB

### Test 3: Add Viewer

1. Approve another Gmail
2. They log in (default role: Viewer)
3. As them:
   - ✅ Can view images
   - ✅ Can view NestDB (read-only)
   - ❌ Cannot annotate
   - ❌ Cannot access /admin
   - ❌ Cannot edit NestDB

### Test 4: Logout

1. Click logout button (top-right)
2. ✅ Redirected to login page
3. ✅ Cannot access any authenticated pages
4. ✅ Health check still works at `/health`

### Test 5: Health Check

```bash
curl http://localhost:5000/health
```

✅ Should return JSON even when logged out

---

## 📝 Code Changes Summary

### Files Modified

1. **`labeller/auth.py`**
   - Added `get_user_role()` - Get user's current role
   - Added `get_user_permissions()` - Get capabilities for role
   - Added `update_user_role()` - Change a user's role
   - Added `get_all_users_with_roles()` - List users with permissions
   - Added `@annotator_required` decorator
   - Added `@db_editor_required` decorator
   - Added `@api_annotator_required` decorator
   - Added `@api_db_editor_required` decorator

2. **`labeller/app.py`**
   - Updated imports to include new decorators
   - Updated session to store role and permissions
   - Updated `/admin` route to show roles
   - Added `/admin/update-role` route
   - Added `/health` public endpoint
   - Protected annotation routes with `@api_annotator_required`
   - Updated `/api/users` to return only logged-in annotators

3. **`labeller/templates/admin_panel.html`**
   - Complete rewrite with role management
   - Shows user roles and permissions
   - Dropdown to change roles
   - Permission indicators (colored dots)
   - 6 stat cards (including role counts)
   - Logout button in header

4. **`labeller/templates/base.html`**
   - Added user info to navbar (picture, name)
   - Added logout button
   - Added admin link (for admins only)
   - Border separator for user section

5. **`data/users.db`**
   - Added `role` column to `users` table
   - Created `permissions` table with role definitions
   - Updated existing admin user to 'admin' role

---

## 🎓 Educational Concepts

### What is RBAC?

**Role-Based Access Control** is a security model where:
- Users are assigned **roles** (Admin, Annotator, Viewer)
- Roles have **permissions** (can_annotate, can_edit_db)
- System checks **permissions** before allowing actions

### Real-World Examples

- **GitHub:** Owner, Maintainer, Write, Read
- **Google Workspace:** Super Admin, Admin, User
- **AWS:** root, IAM policies
- **WordPress:** Administrator, Editor, Author, Subscriber

### Why Use RBAC?

1. **Security:** Least privilege principle (give minimum needed access)
2. **Simplicity:** Easier than managing individual permissions
3. **Scalability:** Easy to add new users with predefined roles
4. **Audit:** Clear who can do what

### Permission Checking Pattern

```python
# Decorator checks permission before function runs
@api_annotator_required
def save_annotations():
    # If we get here, user has annotate permission
    pass

# Inside decorator:
def api_annotator_required(f):
    def wrapper(*args, **kwargs):
        perms = get_user_permissions(session['user']['email'])
        if not perms['can_annotate']:
            return jsonify({'error': 'No permission'}), 403
        return f(*args, **kwargs)  # Allow function to run
    return wrapper
```

---

## 🚨 Security Notes

### What's Protected

- ✅ All annotation operations
- ✅ All database edits
- ✅ User management (admin only)
- ✅ Project creation/deletion
- ✅ Role changes

### What's Public

- ✅ Login page
- ✅ Health check endpoint (`/health`)
- ✅ OAuth callback (needs to be public)

### Best Practices

1. **Don't make everyone admin** - Only trusted people
2. **Start with Viewer** - Default role is safest
3. **Review permissions regularly** - Check who has what access
4. **Remove old users** - Deactivate people who leave
5. **Use annotator role for most** - It's the sweet spot

---

## 🔧 Troubleshooting

### "Annotator permission required" error

**Problem:** User tries to annotate but sees this error

**Fix:**
1. Go to admin panel
2. Find their email in users table
3. Change role to "Annotator" or "Admin"
4. They need to log out and back in

### User can't see admin panel

**Problem:** User clicks Admin link but gets 403 error

**Fix:**
1. Check their role in admin panel
2. Change to "Admin" role
3. They need to log out and back in

### Health check shows "Error"

**Problem:** System dashboard shows Nestperts as "Error"

**Fix:**
1. Check if Nestperts is running
2. Visit http://localhost:5000/health directly
3. Should work even when logged out
4. If still failing, check logs

### Can't change own role

**Problem:** Admin tries to change their own role

**Why:** Safety feature - prevents you from accidentally removing your own admin access

**Fix:** Have another admin change your role, or edit database directly:
```bash
.venv/bin/python3 -c "
from labeller.auth import update_user_role
update_user_role('your@email.com', 'admin')
"
```

---

## 📚 Next Steps

### Immediate

1. **Test the system:**
   - Log in as admin
   - Try changing roles
   - Test logout

2. **Add your team:**
   - Add their emails in admin panel
   - Assign appropriate roles
   - Have them test login

### Optional Enhancements

1. **Email Notifications:**
   - Send email when user is approved
   - Notify when role changes

2. **Activity Logging:**
   - Track who changed what
   - Audit trail for role changes
   - Log annotation activities

3. **Advanced Permissions:**
   - Per-project permissions
   - Time-limited access
   - IP restrictions

4. **Bulk Operations:**
   - Import users from CSV
   - Bulk role assignments
   - Export user list

---

## 🎉 Summary

You now have a production-grade RBAC system that:
- ✅ Integrates authentication with workflow
- ✅ Controls who can annotate, edit DB, and manage users
- ✅ Shows real user names (not fake usernames)
- ✅ Has a beautiful admin panel
- ✅ Includes logout buttons everywhere
- ✅ Works with health monitoring

All users are now real, authenticated people with appropriate permissions!
