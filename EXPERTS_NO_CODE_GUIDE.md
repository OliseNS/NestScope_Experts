# NestDB Version Control - Expert User Guide

## ✨ The Most Important Thing: You Don't Need to Write Any Code!

Version control in NestDB is **100% automatic**. Just use the interface normally - everything is tracked behind the scenes.

---

## 🎯 What You Need to Know (30 Second Version)

1. **Edit data in NestDB** → Changes are automatically saved to version history
2. **See "committed to version history"** in success messages → It's working!
3. **Go to Version History tab** → See all your changes
4. **Made a mistake?** → Click "Rollback to Here" on any previous version

**That's it.** No Git commands, no manual saves, no code.

---

## 📋 Complete Workflow (Step-by-Step)

### Step 1: Edit Data (Normal Workflow)

1. Open NestDB at `http://localhost:8501`
2. Go to **"Table Browser"** tab
3. Select a table from the dropdown
4. Toggle **"Edit Mode"** ON
5. Click on any cell to edit its value
6. Click **"Save Changes"** button

**What happens automatically:**
- ✅ Your changes are saved to the database
- ✅ The database is exported to a text file (SQL dump)
- ✅ A commit is created with your changes and timestamp
- ✅ You see: "Successfully saved 3 row(s) and automatically committed to version history (commit `a3f5d2c`)"

**You did:** Edit → Save
**System did:** Export → Commit → Track → Notify

---

### Step 2: View Version History (Optional)

1. Go to **"Version History"** tab
2. See the green banner: "✅ Auto-Versioning Active - All changes automatically saved to version history"
3. Scroll through the list of commits (newest first)
4. Each commit shows:
   - Date and time
   - What changed (e.g., "Updated 3 row(s) in tblColonyTotals")
   - Who made the change

**What you do:** Look at the list
**What you see:** Complete history of all database changes

---

### Step 3: View What Changed (Optional)

1. Find a commit in the Version History list
2. Click **"View Diff"**
3. See the exact SQL statements that changed:
   ```diff
   +INSERT INTO observations VALUES (12345, 'Brown Pelican', 5200);
   -INSERT INTO observations VALUES (12345, 'Brown Pelican', 5000);
   ```
   - `+` means "added" (new value: 5200 birds)
   - `-` means "removed" (old value: 5000 birds)

**What you do:** Click "View Diff"
**What you see:** Exact changes in human-readable format

---

### Step 4: Rollback Mistakes (If Needed)

1. Find the commit you want to restore to
2. Click **"Rollback to Here"** button
3. Read the warning message
4. Enter your email for the audit trail
5. Click **"Yes, Rollback"**
6. Wait 10-30 seconds (system creates safety backup first)
7. See success message: "Database rolled back successfully!"

**What happens automatically:**
- ✅ System creates a safety snapshot (backup)
- ✅ Database is restored to the selected version
- ✅ Rollback is recorded as a new commit (history not erased)
- ✅ You can rollback the rollback if needed!

---

## 💡 Common Questions

### "Do I need to learn Git?"
**No.** Git is running in the background, but you never interact with it directly. The UI handles everything.

### "Do I need to remember to create commits?"
**No.** Commits happen automatically every time you save changes. You can't forget!

### "What if I forget to create a checkpoint?"
**No problem.** Every single change is already a checkpoint. You can rollback to any moment.

### "Can I break the version history?"
**No.** The system is read-only for history. You can rollback, but you can never delete or corrupt the history.

### "Do I need to install anything?"
**No.** If you can access NestDB in your browser, version control is already active.

### "What if versioning fails?"
You'll still be able to save changes (database writes work normally). You just won't have version history for that specific change. The system logs errors and continues working.

---

## 🔍 How to Tell It's Working

### Method 1: Success Messages
When you save changes, look for this message:
```
✅ Successfully saved 3 row(s) and automatically committed to version history (commit a3f5d2c)
```

If you see `committed to version history`, it's working!

### Method 2: Green Banner
At the top of NestDB, look for:
```
✅ Auto-Versioning Active - All changes automatically saved to version history (15 commits tracked)
```

### Method 3: Version History Tab
Go to "Version History" tab. If you see a list of commits (not an error message), it's working!

---

## 🎓 What's Happening Behind the Scenes (For the Curious)

When you click "Save Changes":
1. **Frontend** sends your edit to the backend API
2. **Backend** executes the SQL UPDATE/INSERT/DELETE
3. **Version Control Service** automatically:
   - Exports database to `bird_data_complete.sql`
   - Runs `git add bird_data_complete.sql`
   - Runs `git commit -m "Updated 3 row(s) in tblColonyTotals"`
   - Returns commit hash to frontend
4. **Frontend** shows "committed to version history (commit abc123)"

**Total time:** Usually < 1 second
**Your effort:** Zero (it's automatic)

---

## 🚨 What If Something Goes Wrong?

### Scenario 1: "Version control is not available"
**Cause:** Git is not installed or initialization failed
**Fix:** Contact your system administrator
**Impact:** You can still use NestDB normally, just no version history

### Scenario 2: "No commits found"
**Cause:** You haven't made any database changes yet
**Fix:** Make a change (edit/add a row) to create the first commit
**Impact:** Normal - history is empty until first change

### Scenario 3: "Rollback failed"
**Cause:** Database file is locked by another process
**Fix:** Close other database connections and try again
**Impact:** Database is unchanged (rollback didn't happen)

---

## 📊 Real-World Example

**Scenario:** Dr. Sarah Chen is updating brown pelican counts for Queen Bess Island.

**Monday 10:00 AM:** Sarah edits pelican count from 5,000 to 5,200
- **Action:** Edits cell → Clicks "Save Changes"
- **Result:** ✅ "Successfully saved and committed to version history (commit `a3f5d2c`)"

**Monday 2:00 PM:** Sarah realizes the AI was correct - it should be 5,000
- **Action:** Opens Version History → Finds commit from 9:00 AM (before her edit) → Clicks "Rollback to Here"
- **Result:** ✅ Count restored to 5,000 in 15 seconds

**Total code written:** Zero
**Total Git commands run:** Zero
**Total manual backups created:** Zero
**Time saved vs. manual approach:** 30 minutes

---

## ✅ Checklist: Am I Doing It Right?

- [ ] I edit data in the Table Browser tab (normal workflow)
- [ ] I click "Save Changes" when done
- [ ] I see "committed to version history" in the success message
- [ ] If I make a mistake, I go to Version History → Rollback
- [ ] I **don't** write any Git commands
- [ ] I **don't** manually export/import database files
- [ ] I **don't** create my own backups (system does it automatically)

If you checked all boxes, you're using it perfectly!

---

## 🎉 Summary

### What You Do:
1. Edit data (normal workflow)
2. Click "Save Changes"
3. See confirmation message

### What the System Does:
1. Save changes to database
2. Export database to text file
3. Commit to version control
4. Track who changed what and when
5. Enable rollback to any previous state
6. Maintain audit trails for scientific integrity

### What You DON'T Do:
- ❌ Write code
- ❌ Run Git commands
- ❌ Manually create commits
- ❌ Export/import files
- ❌ Remember to save versions

**It's like auto-save in Microsoft Word, but for an entire database with full undo history.**

---

## 🔗 Need More Help?

- **Quick start:** Just use NestDB normally - versioning is automatic
- **Detailed docs:** See `VERSION_CONTROL_SUMMARY.md`
- **Technical details:** See `data/GIT_VERSIONING_README.md`
- **Test isolation:** Run `./verify_git_isolation.sh`

---

**Remember:** If you can edit a spreadsheet, you can use NestDB version control. No code required! 🚀
