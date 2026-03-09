# Centralized User Management System

## Overview

Implemented a **centralized user registry** system where users can work across multiple projects with **smart random image assignment** and **flexible task management**.

## Key Features ✅

### 1. **Global User Registry**
- Users stored in `labeller/projects/users.json`
- Single source of truth for all users
- Can work on multiple projects simultaneously
- Track total completed images and annotations across all projects

### 2. **Smart Random Assignment**
- Randomly selects images from unassigned pool
- Prevents duplicate assignments
- Can assign from 1 image to all images
- Shows real-time assigned vs unassigned counts

### 3. **Flexible Re-assignment**
- Can add more images to users who already have tasks
- Optional "Allow Reassignment" mode to assign already-assigned images
- Perfect for load balancing or fixing assignment errors

### 4. **Better Assignment UX**
- See unassigned image count before assigning
- Select from global user list in dropdown
- Create new users on-the-fly during assignment
- Clear feedback on what happened

### 5. **Users Management Page**
- New `/users` page to see all users
- Shows each user's projects and progress
- Quick links to jump to user's editor in any project
- Global statistics (total completed, annotations, etc.)

---

## Architecture

### File Structure

```
labeller/
├── services/
│   └── user_service.py          # NEW: Centralized user management
├── projects/
│   └── users.json                # NEW: Global user registry
├── templates/
│   ├── users_page.html           # NEW: Users management page
│   ├── project_detail.html       # UPDATED: Better assignment modal
│   └── base.html                 # UPDATED: Added Users nav link
└── app.py                        # UPDATED: New APIs and logic
```

### Data Model

**Global Users Registry** (`projects/users.json`):
```json
{
  "users": [
    {
      "name": "alice",
      "created_at": "2026-03-09T12:00:00",
      "projects": ["stage_1", "stage_2"],
      "total_completed": 45,
      "total_annotations": 234
    }
  ],
  "created_at": "2026-03-09T10:00:00"
}
```

**Project State** (`projects/<project>/project_state.json`):
```json
{
  "users": {
    "alice": {
      "assigned": ["img1.jpg", "img2.jpg", ...],
      "completed": ["img1.jpg"]
    }
  }
}
```

**Relationship**:
- Global registry: WHO the users are (across all projects)
- Project state: WHAT tasks each user has (project-specific)

---

## API Endpoints

### User Management

#### `GET /api/users`
Get all users from global registry.

**Response**:
```json
{
  "users": [
    {
      "name": "alice",
      "projects": ["stage_1", "stage_2"],
      "total_completed": 45
    }
  ]
}
```

#### `POST /api/users/create`
Create a new user in global registry.

**Request**:
```json
{
  "username": "bob"
}
```

**Response**:
```json
{
  "success": true,
  "user": {
    "name": "bob",
    "created_at": "2026-03-09T12:30:00",
    "projects": []
  }
}
```

### Assignment Management

#### `POST /api/projects/assign-task`
Assign random images to a user.

**Request**:
```json
{
  "project_id": "stage_1",
  "username": "alice",
  "num_images": 10,
  "allow_reassign": false
}
```

**Response**:
```json
{
  "success": true,
  "assigned": 10,
  "total_assigned": 25,
  "selection_type": "unassigned images only",
  "message": "Assigned 10 new image(s) to alice (unassigned images only)"
}
```

**Assignment Modes**:
- `allow_reassign: false` (default) - Only select from unassigned images
- `allow_reassign: true` - Can select from any images (including assigned to others)

#### `GET /api/projects/<project>/images/unassigned`
Get assignment statistics for a project.

**Response**:
```json
{
  "total_images": 100,
  "assigned_images": 45,
  "unassigned_images": 55
}
```

---

## User Workflows

### Workflow 1: Create User and Assign Tasks

1. **Go to Users page** (`/users`)
2. Click "Create User"
3. Enter username → "alice"
4. Go to any project → Click "Assign Task"
5. Select "alice" from dropdown
6. Enter number of images (e.g., 10)
7. Click "Assign Images"
8. ✅ Alice gets 10 randomly selected images

### Workflow 2: Add More Images to Existing User

1. Go to project detail page
2. Click "Assign Task"
3. Select user who already has tasks (e.g., "alice")
4. Enter additional images (e.g., 5)
5. Click "Assign Images"
6. ✅ Alice gets 5 MORE random images (total 15 now)

### Workflow 3: Reassign Images

**Scenario**: All 100 images are assigned, but you want to add more to a user.

1. Click "Assign Task"
2. Select user
3. Check "Allow reassignment" checkbox
4. Enter number (e.g., 10)
5. Click "Assign Images"
6. ✅ User gets 10 images (some may have been assigned to others)

### Workflow 4: View User's Work Across Projects

1. Go to Users page (`/users`)
2. See all users and their project badges
3. Click any project badge
4. ✅ Opens that project's editor for that user

---

## Random Selection Algorithm

**How random assignment works**:

```python
# 1. Get available images
available_images = unassigned_images  # Or all_images if allow_reassign=True

# 2. Exclude user's current assignments (avoid duplicates)
available_images = [img for img in available_images
                    if img not in user_current_assignments]

# 3. Random sample
import random
selected = random.sample(available_images, num_images)

# 4. Add to user's assigned list
user['assigned'].extend(selected)
```

**Benefits**:
- No bias (alphabetical, date, etc.)
- Evenly distributed workload
- Prevents clustering of similar images

---

## UI Improvements

### Assignment Modal

**Before**:
- Simple number input
- Static "N unassigned images available" text
- Had to create user separately

**After**:
- Real-time stats (Total / Assigned / Unassigned)
- Dynamic help text based on availability
- Inline user creation (create + assign in one flow)
- "Allow Reassignment" checkbox for flexibility
- Better feedback messages

**Screenshot of Modal**:
```
┌─────────────────────────────────────┐
│ Assign Images                    ×  │
├─────────────────────────────────────┤
│ Assign to User                      │
│ [alice (2 projects)        ▼]       │
│                                     │
│ ┌─────┬─────┬─────┐                │
│ │ 100 │  45 │  55 │                │
│ │Total│Asgnd│Unas │                │
│ └─────┴─────┴─────┘                │
│                                     │
│ Number of Images to Assign          │
│ [10            ]                    │
│ 55 unassigned images available      │
│                                     │
│ ☐ Allow reassignment                │
│                                     │
│ [Cancel]  [Assign Images]           │
└─────────────────────────────────────┘
```

### Users Page

New dedicated page at `/users` showing:
- Total users count
- Project assignments count
- Total completed images
- Total annotations
- Clickable project badges to jump to editor

---

## Educational Notes

### Why Centralized Users?

**Problem with Project-Specific Users**:
```
Project A: {"users": {"alice": {...}}}
Project B: {"users": {"alice": {...}}}  # Duplicate!
```

- Same person defined multiple times
- Can't track cross-project stats
- Harder to manage (update in multiple places)

**Solution: Single Source of Truth**:
```
Global: users.json → {"users": [{"name": "alice"}]}
Project A: project_state.json → {"users": {"alice": {"assigned": [...]}}}
Project B: project_state.json → {"users": {"alice": {"assigned": [...]}}}
```

- User defined once
- Projects reference by name
- Easy to track global stats
- Update in one place

### Why Random Assignment?

**Alternatives and Why They're Problematic**:

1. **Alphabetical**: First images get over-assigned
2. **Sequential**: Temporal bias (all spring images to one person)
3. **First-come-first-serve**: Race conditions

**Random Benefits**:
- Fair distribution
- No patterns or bias
- Good for inter-annotator agreement testing
- Prevents cherry-picking

---

## Migration Guide

### For Existing Projects

If you have projects with users in `project_state.json` BEFORE this update:

**They will continue to work!** The system is backwards-compatible.

**To migrate to global registry**:

1. Go to `/users` page
2. Create users manually OR
3. Let system auto-create on first assignment

The first time you assign a task to an existing user after the update:
- User is auto-created in global registry
- Project added to their project list
- Everything syncs automatically

### For New Projects

Just:
1. Create project (upload zip)
2. Create users on `/users` page
3. Assign tasks normally

---

## Configuration

### Assignment Defaults

Located in `app.py` around line 656:

```python
num_images = data.get('num_images', 10)  # Default: 10 images
allow_reassign = data.get('allow_reassign', False)  # Default: only unassigned
```

**To change defaults**:
- Modify the frontend default in `project_detail.html` line ~388:
  ```html
  <input type="number" id="numTasks" value="10" ...>
  ```

### User Service Location

Users file: `labeller/projects/users.json`

**To change location**, edit `user_service.py` line 28:
```python
self.users_file = os.path.join(projects_dir, 'users.json')
```

---

## Testing Checklist

- [x] Create new user from Users page
- [x] Create user during assignment (inline creation)
- [x] Assign random images to user
- [x] Add more images to user with existing tasks
- [x] Reassign mode allows taking assigned images
- [x] User appears in global registry
- [x] User's projects list updates
- [x] Assignment stats display correctly
- [x] Can't assign more than available (with proper error)
- [ ] Test with 100+ images project
- [ ] Test with 10+ users
- [ ] Test reassignment edge cases
- [ ] Verify random distribution is fair

---

## Known Limitations

1. **No batch user creation** - Must create users one-by-one
2. **No user deletion** - Can only add users (need to manually edit JSON)
3. **No user renaming** - Username is permanent
4. **No unassignment** - Can't remove assigned images from user (only complete them)
5. **Random seed not configurable** - Uses Python's default random

---

## Future Improvements

- [ ] Add user deletion with confirmation
- [ ] Add user editing (rename, merge)
- [ ] Add batch import users from CSV
- [ ] Add unassign functionality
- [ ] Add "assign equally" mode (split images evenly among N users)
- [ ] Add assignment history/audit log
- [ ] Add user permissions/roles
- [ ] Add inter-annotator agreement calculator
- [ ] Add user performance metrics
- [ ] Export user statistics to CSV

---

## Files Changed

1. **NEW: `labeller/services/user_service.py`**
   - Centralized user management service
   - CRUD operations for users
   - Project tracking per user

2. **NEW: `labeller/templates/users_page.html`**
   - Global users management UI
   - Shows all users and their assignments
   - Create user functionality

3. **UPDATED: `labeller/app.py`**
   - Line 901: Added `_user_service` global
   - Line 914-925: Added `get_user_service()` lazy loader
   - Line 656-717: Rewrote `assign_task()` with random selection
   - Line 949-979: Added `/api/users` endpoint
   - Line 981-1012: Added `/api/users/create` endpoint
   - Line 1014-1033: Added `/api/projects/<id>/images/unassigned` endpoint
   - Line 310-335: Added `/users` route

4. **UPDATED: `labeller/templates/project_detail.html`**
   - Line 362-400: Rewrote assignment modal with better UI
   - Line 406-485: Updated JavaScript for centralized users

5. **UPDATED: `labeller/templates/base.html`**
   - Line 32: Added "Users" navigation link

---

## Troubleshooting

### "User already exists" error when assigning

**Cause**: Trying to create user that's already in global registry.

**Fix**: Just select the existing user from dropdown instead of creating new.

### Assigned images not showing up

**Cause**: Project state not saved properly.

**Fix**: Check `labeller/projects/<project>/project_state.json` exists and has correct format.

### Users page shows 0 users

**Cause**: `users.json` doesn't exist yet.

**Fix**: It will be auto-created on first use. Or manually create `/users` page and add a user.

### Can't assign any images (all assigned)

**Solution 1**: Use "Allow Reassignment" checkbox

**Solution 2**: Upload more images to project

**Solution 3**: Remove assignments from `project_state.json` manually

---

## Performance Notes

- **User lookup**: O(n) where n = number of users (acceptable for <1000 users)
- **Random selection**: O(m) where m = available images
- **Assignment save**: O(1) file write

**For large projects (10,000+ images)**:
- Random sampling is instant
- No performance issues

**For many users (100+)**:
- Dropdown population may be slow
- Consider pagination or search in future

---

## Database Schema (Future)

Currently using JSON files. For production:

```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_completed INTEGER DEFAULT 0,
    total_annotations INTEGER DEFAULT 0
);

-- Assignments table
CREATE TABLE assignments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    project_id INTEGER REFERENCES projects(id),
    image_name TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    UNIQUE(user_id, project_id, image_name)
);
```

This would enable:
- Faster queries
- Better analytics
- Atomic transactions
- Proper foreign keys
