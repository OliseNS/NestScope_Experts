# Database Rollback Guide
**NestScope Database Version Control & Rollback System**

---

## 🎯 Overview

Every database change in NestScope is automatically tracked with full version control, allowing you to rollback to any previous state with a single click.

**Two-Layer System:**
1. **Git Version Control** - Full database snapshots (for rollback)
2. **Change Tracker** - Detailed column-level audit trail (for visibility)

---

## 📍 How to Access Rollback

### Step 1: Open NestDB
Navigate to: **http://localhost:8501** (or your Streamlit frontend)

### Step 2: Go to Version Control Tab
Click the **"Version Control"** tab (📜 icon) in the top navigation

### Step 3: View Commit History
You'll see a list of all database changes with:
- 👤 User who made the change (with profile picture)
- 📅 Timestamp
- 🔧 Operation type (UPDATE, INSERT, DELETE, SQL_QUERY)
- 📊 Table affected
- 📝 Description of changes

### Step 4: Expand to See Details (Optional)
Click **"Show Changes"** on any commit to see:
- Exact columns that changed
- Old value → New value for each column
- Color-coded diff (red = before, green = after)

### Step 5: Rollback
Click the **"↩️ Rollback"** button on any commit (except the most recent one)

---

## ⚠️ Rollback Safety Features

### Automatic Safety Snapshot
Before every rollback, the system automatically creates a backup snapshot of your current database in:
```
data/snapshots/YYYY-MM-DD_HH-MM-SS_pre-rollback_bird_data_complete.db
```

### Confirmation Dialog
You'll see a warning dialog:
```
⚠️ WARNING: This will rollback the database to commit abc12345.

All changes after this commit will be undone.
A safety snapshot will be created.

Are you sure?
```

### Email Attribution
You'll be asked to enter your email for the audit trail. This records WHO performed the rollback.

### Non-Destructive
Rollbacks create a NEW commit in Git history (they don't delete history). This means:
- ✅ You can see WHEN a rollback happened
- ✅ You can see WHO performed the rollback
- ✅ You can rollback a rollback (undo the undo)
- ✅ Full audit trail is preserved

---

## 🔍 When to Use Rollback

### ✅ Good Use Cases:
1. **Accidental bulk update** - "I updated 1000 rows by mistake"
2. **Incorrect data entry** - "I entered the wrong species for an entire colony"
3. **Testing gone wrong** - "I ran a test query that modified production data"
4. **Want to undo recent changes** - "Rollback to yesterday's state"

### ❌ Not Recommended:
1. **Reverting old changes while keeping new ones** - Rollback undoes ALL changes after the target commit, not just that one commit
2. **Routine data corrections** - Use Edit Mode for small fixes instead

---

## 📊 Understanding the Version History

### Commit Cards Show:

**Header:**
- 🟢 **UPDATE** badge (green) - Row was modified
- 🔵 **INSERT** badge (blue) - New row added
- 🔴 **DELETE** badge (red) - Row deleted
- 🟡 **SQL_QUERY** badge (yellow) - Custom SQL executed

**User Info:**
- Profile picture (if logged in via Nestperts)
- Email address
- Full name (if available)

**Metadata:**
- Table name affected
- Number of rows affected
- Timestamp (YYYY-MM-DD HH:MM:SS)

**Changes Detail:**
- Click "Show Changes" to expand
- Table showing column-by-column diffs
- Color-coded: red background = old value, green background = new value

---

## 🛠️ Rollback Process (Behind the Scenes)

When you click "↩️ Rollback", here's what happens:

```
1. Create safety snapshot
   └─ Copy current database to snapshots/

2. Checkout SQL dump from target commit
   └─ Git retrieves the SQL file as it was at that commit

3. Drop and rebuild database
   └─ Delete current .db file
   └─ Import SQL dump to create restored database

4. Create rollback commit
   └─ Git commits the restoration as a new commit
   └─ Commit message: "Rollback to commit abc12345"

5. Reload UI
   └─ Refresh version history
   └─ Reload table data (if viewing a table)
```

**Total time:** Usually 1-5 seconds depending on database size.

---

## 🚨 Troubleshooting

### Problem: No Rollback Buttons Visible

**Cause 1:** You're looking at the most recent commit
- **Solution:** Rollback buttons only appear on commits that have newer commits after them (you can't rollback to "right now")

**Cause 2:** No Git commits exist yet
- **Solution:** Make at least one database change to create your first commit

**Cause 3:** Backend not running
- **Solution:** Ensure FastAPI backend is running: `http://localhost:8000/health`

### Problem: Rollback Failed

**Check:**
1. **Backend logs:** `logs/server.log` for error details
2. **Git status:** `cd data/ && git status` to see Git repo state
3. **Snapshot created:** Check `data/snapshots/` for safety backup
4. **Disk space:** Ensure enough space for database operations

**Recovery:**
If rollback fails, your data is safe because:
- Original database is in `data/snapshots/` (timestamped)
- Git history is intact
- You can manually restore from snapshot

### Problem: Rollback Button Greyed Out

**Cause:** You're on the Version Control tab but backend is still processing
- **Solution:** Wait for version history to fully load, then buttons will activate

---

## 📖 Example Scenarios

### Scenario 1: Undo Last Hour's Changes

**Situation:** You accidentally bulk-updated 500 rows with wrong data 30 minutes ago.

**Solution:**
1. Go to Version Control tab
2. Find the commit from 30 minutes ago (before your bulk update)
3. Click "↩️ Rollback" on that commit
4. Confirm the warning dialog
5. Enter your email
6. Done! Database restored to 30 minutes ago

**Result:** All changes after that commit are undone. Safety snapshot created.

---

### Scenario 2: Compare Before/After

**Situation:** You updated species classifications but want to see what changed.

**Solution:**
1. Go to Version Control tab
2. Find your recent commit (shows UPDATE badge)
3. Click "Show Changes" button
4. See detailed table showing:
   - Column: species
   - Before: Brown Pelican
   - After: American White Pelican

**Result:** You can verify your changes without rolling back.

---

### Scenario 3: Rollback a Rollback (Undo Undo)

**Situation:** You rolled back but realized you actually needed those changes.

**Solution:**
1. Go to Version Control tab
2. Find the commit that says "Rollback to commit abc12345"
3. Look at the commits BEFORE this rollback commit
4. Find your original changes (they're still in history!)
5. Click "↩️ Rollback" to the commit right BEFORE the rollback

**Result:** You've restored the state before the rollback (effectively undoing the undo).

---

## 🎓 Educational Note: How Git Tracks Databases

### Why Not Version the .db File Directly?

**Problem:** SQLite .db files are binary. Git can't show meaningful diffs.

**Solution:** Version SQL dumps (text files) instead.

**Example:**

**Binary .db file (Git sees):**
```
01001001 01001110 01010011 01000101 01010010 01010100
```
❌ Can't see what changed

**SQL dump file (Git sees):**
```sql
-INSERT INTO observations VALUES (123, 'Brown Pelican', 100);
+INSERT INTO observations VALUES (123, 'Brown Pelican', 150);
```
✅ Clear: count changed from 100 to 150

### Why Two Systems (Git + Change Tracker)?

**Git Version Control:**
- Purpose: Full database backup & restoration
- Granularity: Entire database
- Use case: "Rollback to 2 hours ago"

**Change Tracker:**
- Purpose: Detailed audit trail
- Granularity: Individual columns
- Use case: "Show me what changed in this row"

**Together:** You get backup capability + audit visibility!

---

## 📊 Version Control Statistics

At the top of the Version Control tab, you'll see:

**Powered by GitHub** (larger, bolder logo)
- Shows that Git is the underlying technology
- Links to GitHub documentation

**Stats Card:**
- 📊 **Total Commits:** How many database changes have been made
- 💾 **DB Size:** Current database size in MB

---

## 🔐 Security & Compliance

### Audit Trail Compliance
Every rollback is tracked with:
- ✅ WHO performed it (email + name)
- ✅ WHEN it happened (timestamp)
- ✅ WHAT was restored (commit hash)
- ✅ WHY (snapshot path for verification)

### Data Safety
- ✅ Automatic snapshots before destructive operations
- ✅ Non-destructive version history (never deletes commits)
- ✅ Multiple recovery paths (Git history + snapshots)
- ✅ Read-only mode for queries (NestChat cannot modify data)

---

## 🚀 Best Practices

### 1. Regular Checkpoints
Create manual checkpoints before major operations:
- Go to SQL Editor tab
- Run a harmless query like: `SELECT 1;`
- Add comment: "Checkpoint before bulk species update"
- This creates a clear restore point

### 2. Descriptive Email Attribution
When rolling back, use your work email (not "test@example.com") so audit trails are meaningful.

### 3. Review Changes Before Rollback
Always click "Show Changes" to verify what you're undoing. Rollback affects ALL changes after the target commit.

### 4. Test Rollback in Development First
If possible, test rollback on a copy of your database before doing it in production.

### 5. Communicate Rollbacks to Team
If multiple people use the database, announce rollbacks so they know recent changes were undone.

---

## 📞 Need Help?

**Check Logs:**
```bash
# Backend logs
tail -f logs/server.log

# Git commit history
cd data/ && git log --oneline
```

**Manual Recovery from Snapshot:**
```bash
# List available snapshots
ls -lh data/snapshots/

# Restore from snapshot (replace timestamp)
cp data/snapshots/2026-03-10_14-30-00_pre-rollback_bird_data_complete.db data/bird_data_complete.db
```

**Contact Support:**
- Check CLAUDE.md for architecture details
- Review VERSIONING_UPGRADE.md for technical explanation
- Open an issue at project repository

---

**Happy version controlling! 🎉**
