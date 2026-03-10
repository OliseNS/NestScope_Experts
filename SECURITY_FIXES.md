# 🚨 CRITICAL SECURITY FIXES - Nestperts

## ⚠️ INCIDENT REPORT

**Date:** 2026-03-10
**Severity:** CRITICAL
**Issue:** Viewer role was able to delete projects
**Status:** ✅ FIXED

---

## 🔓 Security Vulnerabilities Found

### 1. PROJECT DELETION - CRITICAL
**Route:** `DELETE /api/projects/<project_folder>/delete`
**Before:** Only required `@api_login_required`
**Problem:** ANY logged-in user (including viewers) could delete entire projects
**Impact:** Data loss, malicious deletion, project sabotage

**After:** `@admin_required`
**Fix:** Only admins can delete projects

### 2. PROJECT CREATION - HIGH
**Route:** `POST /api/projects/create`
**Before:** Only required `@api_login_required`
**Problem:** Viewers could create projects
**Impact:** Unauthorized project creation, storage abuse

**After:** `@api_annotator_required`
**Fix:** Only annotators and admins can create projects

### 3. TASK ASSIGNMENT - HIGH
**Route:** `POST /api/projects/assign-task`
**Before:** Only required `@api_login_required`
**Problem:** Viewers could assign tasks to users
**Impact:** Workflow manipulation, unauthorized task distribution

**After:** `@admin_required`
**Fix:** Only admins can assign tasks

### 4. IMAGE DELETION - HIGH
**Route:** `POST /api/delete_image`
**Before:** NO AUTHENTICATION AT ALL
**Problem:** Anyone could delete images (even unauthenticated!)
**Impact:** Dataset corruption, data loss

**After:** `@api_annotator_required`
**Fix:** Only annotators and admins can delete images

### 5. USER CREATION - MEDIUM
**Route:** `POST /api/users/create`
**Before:** NO AUTHENTICATION AT ALL
**Problem:** Anyone could create users
**Impact:** Unauthorized user creation

**After:** `@admin_required`
**Fix:** Only admins can create users

### 6. UNASSIGNED IMAGES ENDPOINT - LOW
**Route:** `GET /api/projects/<project_folder>/images/unassigned`
**Before:** NO AUTHENTICATION AT ALL
**Problem:** Anyone could view project information
**Impact:** Information disclosure

**After:** `@api_login_required`
**Fix:** Requires authentication to view project info

---

## 🛡️ Security Model (RBAC)

### Role Permissions Matrix

| Action | Viewer | Annotator | Admin |
|--------|--------|-----------|-------|
| View projects | ✅ | ✅ | ✅ |
| View images | ✅ | ✅ | ✅ |
| View database | ✅ | ✅ | ✅ |
| Annotate images | ❌ | ✅ | ✅ |
| Delete images | ❌ | ✅ | ✅ |
| Create projects | ❌ | ✅ | ✅ |
| Delete projects | ❌ | ❌ | ✅ |
| Assign tasks | ❌ | ❌ | ✅ |
| Edit database | ❌ | ❌ | ✅ |
| Manage users | ❌ | ❌ | ✅ |
| Create users | ❌ | ❌ | ✅ |

---

## 🔧 Technical Details

### Decorator Usage

**Authentication Levels:**
1. `@login_required` - HTML page protection (redirects to login)
2. `@api_login_required` - API protection (returns 401 JSON error)
3. `@annotator_required` - Requires annotator or admin role
4. `@api_annotator_required` - API version of annotator check
5. `@admin_required` - Requires admin role
6. `@api_db_editor_required` - Requires database edit permission (admin only)

### Before vs After

```python
# BEFORE (VULNERABLE)
@app.route('/api/projects/<project_folder>/delete', methods=['DELETE'])
@api_login_required  # ANY logged-in user!
def delete_project(project_folder):
    # Delete entire project...

# AFTER (SECURE)
@app.route('/api/projects/<project_folder>/delete', methods=['DELETE'])
@admin_required  # ONLY admins!
def delete_project(project_folder):
    # Delete entire project...
```

---

## ✅ Routes Now Properly Protected

### Admin-Only Routes
```python
DELETE /api/projects/<project_folder>/delete  # Delete projects
POST   /api/projects/assign-task               # Assign tasks
POST   /api/users/create                       # Create users
POST   /admin/add-email                        # Add approved emails
POST   /admin/remove-email                     # Remove approved emails
POST   /admin/update-role                      # Change user roles
GET    /admin                                  # Admin panel
```

### Annotator+ Routes (Annotators & Admins)
```python
POST /api/projects/create          # Create projects
POST /api/save_annotations         # Save annotations
POST /api/sam_segment              # Segmentation
POST /api/classify_crop            # Classification
POST /api/delete_image             # Delete images
```

### Authenticated Routes (All logged-in users)
```python
GET  /                             # Projects dashboard
GET  /project/<project_folder>     # Project detail
GET  /users                        # Users page
GET  /nestdb                       # Database viewer
GET  /help                         # Help page
GET  /api/users                    # Get users list
GET  /api/projects/<>/images/unassigned  # Unassigned count
```

### Public Routes (No auth required)
```python
GET  /login                        # Login page
GET  /auth/google                  # OAuth redirect
GET  /auth/google/callback         # OAuth callback
GET  /health                       # Health check
```

---

## 🧪 Testing Security

### Test Case 1: Viewer Cannot Delete Project
```bash
# Log in as viewer
# Try to delete project
curl -X DELETE http://localhost:5000/api/projects/test-project/delete

# Expected: 403 Forbidden
# Response: {"error": "Admin access required"}
```

### Test Case 2: Viewer Cannot Create Project
```bash
# Log in as viewer
# Try to create project
curl -X POST http://localhost:5000/api/projects/create

# Expected: 403 Forbidden
# Response: {"error": "Annotator permission required"}
```

### Test Case 3: Viewer Cannot Assign Tasks
```bash
# Log in as viewer
# Try to assign task
curl -X POST http://localhost:5000/api/projects/assign-task

# Expected: 403 Forbidden
# Response: {"error": "Admin access required"}
```

### Test Case 4: Unauthenticated Cannot Delete Image
```bash
# No authentication
curl -X POST http://localhost:5000/api/delete_image

# Expected: 401 Unauthorized
# Response: {"error": "Authentication required"}
```

---

## 📋 Audit Checklist

- [x] All POST routes protected
- [x] All DELETE routes protected
- [x] All PUT routes protected
- [x] Proper role checks on sensitive operations
- [x] Admin-only operations restricted
- [x] Annotator operations restricted to annotators+
- [x] Public endpoints minimal (login, health)
- [x] API error handling (401, 403)
- [x] Session-based authentication
- [x] OAuth integration secure

---

## 🚀 Deployment Steps

### Immediate Actions Required

1. **Restart Nestperts:**
   ```bash
   # Stop current instance
   # Start with fixed code
   .venv/bin/python3 labeller/app.py --data labeller/nestvision
   ```

2. **Audit Existing Users:**
   - Go to `/admin`
   - Review all user roles
   - Ensure viewers have correct role

3. **Check for Damage:**
   - Review recent project deletions
   - Check logs for unauthorized actions
   - Verify project integrity

4. **Notify Users:**
   - Inform team about security fix
   - Ask users to log out and back in
   - Verify roles are correct

---

## 🔐 Best Practices Going Forward

### Code Review Checklist

Before merging any new routes:
- [ ] Does it modify data? → Requires permission check
- [ ] Does it delete data? → Requires admin permission
- [ ] Does it create resources? → Requires appropriate role
- [ ] Is it a GET request? → Still needs auth for sensitive data
- [ ] Is it an API endpoint? → Use `@api_*_required` decorators
- [ ] Is it a page? → Use `@*_required` decorators

### Security Testing

For every new feature:
1. Test as **viewer** (should be most restricted)
2. Test as **annotator** (should have annotation access)
3. Test as **admin** (should have full access)
4. Test **unauthenticated** (should only access login/health)

### Logging

Add audit logging for sensitive operations:
```python
import logging
logger = logging.getLogger(__name__)

@app.route('/api/projects/<project_folder>/delete', methods=['DELETE'])
@admin_required
def delete_project(project_folder):
    user_email = session['user']['email']
    logger.warning(f"🚨 PROJECT DELETION by {user_email}: {project_folder}")
    # ... deletion code
```

---

## 📊 Impact Assessment

### Severity: CRITICAL
**Why:** Viewers could delete entire projects, causing permanent data loss

### Risk: HIGH
**Why:** Multiple routes were under-protected or completely unprotected

### Likelihood: HIGH
**Why:** Any curious user clicking around could trigger these actions

### Business Impact: HIGH
**Why:**
- Data loss (projects, images, annotations)
- Workflow disruption (unauthorized task assignment)
- Storage abuse (unauthorized project creation)
- Trust issues (security breach)

---

## ✅ Resolution

**Status:** All vulnerabilities patched
**Date Fixed:** 2026-03-10
**Verification:** Manual testing completed
**Code Review:** Complete
**Deployment:** Ready

### Files Modified
- `labeller/app.py` - Added proper decorators to 6 routes

### No Database Changes Required
- Permission system already in place
- Just enforcement was missing

### No Breaking Changes
- Existing functionality preserved
- Only security improved

---

## 📝 Lessons Learned

1. **Always protect POST/DELETE/PUT routes** - Default to requiring auth
2. **Use strongest permission needed** - If data can be lost, require admin
3. **Test with different roles** - Don't just test as admin
4. **Code review for security** - Check every new route
5. **Security by default** - Make protected routes the default

---

## 🎯 Recommendations

### Immediate (Done ✅)
- [x] Fix critical vulnerabilities
- [x] Add proper decorators
- [x] Test all roles

### Short-term (Next Sprint)
- [ ] Add audit logging for sensitive operations
- [ ] Add rate limiting to prevent abuse
- [ ] Add IP-based access control (optional)
- [ ] Add 2FA for admin accounts (optional)

### Long-term
- [ ] Penetration testing
- [ ] Security audit by external party
- [ ] Automated security scanning in CI/CD
- [ ] Security training for developers

---

## 📞 Contact

For security issues or questions:
- Review RBAC_SETUP.md for role details
- Check AUTH_SETUP.md for authentication flow
- Test changes in development before production

---

## ⚡ Quick Reference

**If you see this error, it's working:**
- `{"error": "Admin access required"}` → 403 from @admin_required
- `{"error": "Annotator permission required"}` → 403 from @annotator_required
- `{"error": "Authentication required"}` → 401 from @api_login_required
- `{"error": "Database edit permission required"}` → 403 from @db_editor_required

**All security fixed! Your data is now protected.** 🛡️
