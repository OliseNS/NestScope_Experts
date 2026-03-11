# Assignment & User Management Fixes

## 🔍 Problems Fixed

### 1. **Duplicate Assignments**
**Problem:** User was assigned 505 images including images already assigned to another user.

**Root Cause:** The assignment logic was correct, but someone checked "Allow Reassignment" when assigning OR there was bad data from before the migration.

**Solution:**
- Cleaned up bad assignments with `fix_nestvision_assignments.py`
- Removed selu.edu user who had 505 duplicate assignments

### 2. **No Way to Remove Bad Assignments**
**Problem:** Once a user was assigned images, there was no way to remove them from the project.

**Solution:** Added new features:
- ✅ Backend endpoint: `/api/projects/<project>/remove-user`
- ✅ UI: Red X button next to each user in Team section
- ✅ Confirmation dialog before removal
- ✅ Keeps label files (preserves work) but removes assignments

## 📊 Before vs After

### Before Cleanup:
```
Team (2):
- olisemekanmarkwe@gmail.com: 20 assigned, 20 completed
- olisemeka.nmarkwe@selu.edu: 505 assigned, 0 completed  ← WRONG!

Total: 525 assignments (more than 505 images!)
```

### After Cleanup:
```
Team (1):
- olisemekanmarkwe@gmail.com: 20 assigned, 20 completed  ✅

Total: 20 assignments (correct!)
```

## 🛠️ Changes Made

### Backend (`labeller/app.py`)

**New Endpoint:**
```python
@app.route('/api/projects/<project_folder>/remove-user', methods=['POST'])
def remove_user_from_project(project_folder):
    """
    Remove a user from a project (unassign all their images).
    Keeps label files but removes user from project_state.json
    """
```

### Frontend (`project_detail.html`)

**UI Changes:**
1. Added remove button (red X) next to each user
2. Button uses email as identifier (not name)
3. Confirmation dialog warns about action
4. Reloads page after successful removal

**JavaScript:**
```javascript
async function removeUserFromProject(userEmail, userName) {
    // Confirms, calls API, shows success toast, reloads
}
```

**CSS:**
```css
.btn-icon-danger:hover {
    background: var(--error);
    color: white;
}
```

## 🚀 How to Use

### Remove a User from Project:
1. Go to project page (e.g., `/project/nestvision`)
2. Find user in "Team" section
3. Click red X button next to their name
4. Confirm removal
5. User is removed, page reloads

### What Happens:
- ✅ User removed from `project_state.json`
- ✅ All their assignments cleared
- ✅ Their **label files are kept** (work preserved)
- ✅ Project stats updated correctly

## 🎓 Educational Notes

### Why Keep Label Files?
When you remove a user from a project, we **keep their labels** because:
- They represent valuable work (annotations)
- They may be referenced by the YOLO model
- You might want to reassign the user later

We only delete the **assignments**, not the **completed work**.

### Assignment Logic Explained
```python
# Get ALL assigned images across all users
assigned_images = set()
for user_data in state['users'].values():
    assigned_images.update(user_data['assigned'])

# Only assign unassigned images (unless allow_reassign=True)
if allow_reassign:
    available = [img for img in all_images if img not in user_current]
else:
    available = [img for img in all_images if img not in assigned_images]
```

**Key Point:** If `allow_reassign=False`, images assigned to **any user** are excluded.

### Why Email as Identifier?
We use email (not name) everywhere now:
- ✅ Editor URLs: `/project/nestvision/editor/olisemekanmarkwe@gmail.com`
- ✅ project_state.json keys: `users["email@example.com"]`
- ✅ API parameters: `user_email`

This prevents the name collision bug we fixed earlier.

## ✅ Current State

After running `fix_nestvision_assignments.py`:

**NestVision Project:**
- Total images: 505
- Assigned to gmail user: 20
- Completed by gmail user: 20
- Unassigned: 485

**No more duplicates!** ✨

## 📝 Future Improvements

Consider adding:
1. **Bulk unassign** - Remove all assignments at once
2. **Reassign** - Transfer images from one user to another
3. **Assignment history** - Track who was assigned what and when
4. **Validation** - Prevent assigning more images than available

---

**Date:** March 10, 2026
**Fixed by:** Claude Code
