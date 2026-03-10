# OAuth User Management Implementation

## Overview
Updated Nestperts to use **Google OAuth exclusively** for user authentication and management. Manual user creation has been removed in favor of automatic user registration through Google sign-in.

## Changes Made

### 1. Users Page (`/users`) - Now Shows OAuth Stats Only

**What Changed:**
- Removed manual "Create User" button and modal
- Updated to fetch users from the authentication database (Google OAuth users only)
- Added user profile pictures from Google accounts
- Shows annotation contributions across all projects

**Key Points:**
- Users are automatically added when they sign in with Google OAuth
- Page displays authenticated users and their project contributions
- Shows statistics: total projects, completed images, total annotations
- Profile pictures are displayed from Google accounts

**Backend Changes:**
- `users_page()` route now uses `get_all_users_with_roles()` from auth module
- Calculates project contributions by scanning project states
- Returns user data including: name, email, picture, role, and stats

### 2. Project Assignment Modal - Enhanced with User Pictures

**What Changed:**
- Replaced plain dropdown with custom dropdown showing user profile pictures
- Users can see profile pictures when selecting assignees
- Removed "Create New User" option from assignment flow
- Only authenticated users (via Google OAuth) appear in the dropdown

**Visual Improvements:**
- Custom dropdown with 40px profile pictures
- Shows user name and project count
- Fallback to initial letter avatar if no picture
- Smooth hover effects and modern styling

**Implementation:**
- Custom CSS for `.custom-dropdown` and `.custom-dropdown-option`
- JavaScript functions: `loadAllUsers()`, `toggleUserDropdown()`, `selectUser()`
- Dropdown closes when clicking outside
- Selected user shown with picture in collapsed state

### 3. API Changes

**Deprecated Endpoint:**
```
POST /api/users/create
```
Now returns 403 Forbidden with message:
```json
{
  "error": "Manual user creation is disabled",
  "message": "Users are automatically created when they sign in with Google OAuth. Please direct users to sign in at /login."
}
```

**Active Endpoint:**
```
GET /api/users
```
Returns authenticated users with profile pictures:
```json
{
  "users": [
    {
      "name": "John Doe",
      "email": "john@example.com",
      "picture": "https://lh3.googleusercontent.com/...",
      "role": "annotator",
      "can_annotate": true
    }
  ]
}
```

## User Flow

### New User Sign-In
1. User visits Nestperts and clicks "Sign in with Google"
2. Google OAuth redirects to Google login
3. User authorizes the application
4. Nestperts receives user info (name, email, picture)
5. User is automatically created in `data/users.db`
6. User is assigned default role based on admin status
7. User can immediately be assigned to projects

### Project Assignment
1. Admin opens project detail page
2. Clicks "Assign Task" button
3. Custom dropdown shows all authenticated users with pictures
4. Admin selects user (can see their face and project count)
5. Specifies number of images to assign
6. Images are assigned to the selected user

## Files Modified

### Templates
- `labeller/templates/users_page.html` - Removed manual user creation UI, added profile pictures
- `labeller/templates/project_detail.html` - Custom dropdown with user pictures

### Backend
- `labeller/app.py`:
  - Updated `users_page()` to use authenticated users only
  - Deprecated `create_user()` API endpoint
  - Enhanced user statistics calculation

### Styling
- Added custom dropdown CSS in `project_detail.html`:
  - `.custom-dropdown` - Main container
  - `.custom-dropdown-selected` - Selected user display
  - `.custom-dropdown-options` - Dropdown options list
  - `.custom-dropdown-option` - Individual user option with picture

## Benefits

1. **Security**: Only Google-authenticated users can access the system
2. **Simplicity**: No manual user management needed
3. **Visual Clarity**: Profile pictures make user selection easier
4. **Consistency**: Single source of truth for user identity
5. **Professional**: Modern UI with real profile pictures

## Testing

To test the new flow:

1. **Sign in with Google:**
   ```
   Visit http://localhost:5000/login
   Sign in with a Google account
   ```

2. **Check Users Page:**
   ```
   Visit http://localhost:5000/users
   Should see authenticated users with profile pictures
   ```

3. **Assign Tasks:**
   ```
   Go to any project detail page
   Click "Assign Task"
   See dropdown with user pictures
   Select a user and assign images
   ```

## Admin Setup

Admins must be configured in the authentication database:

```bash
cd labeller
python setup_auth.py
```

This script:
- Initializes `data/users.db`
- Prompts for admin email addresses
- Sets up approved email list
- Creates permissions table

## Notes

- Profile pictures are cached from Google CDN
- Fallback to initial letter avatar if picture unavailable
- Users must have `can_annotate` permission to appear in assignment dropdown
- The old UserService (project-based users.json) is no longer used for user management
- Project state files still track user assignments per project
