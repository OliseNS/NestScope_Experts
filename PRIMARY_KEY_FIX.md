# Primary Key Fix for NestDB Updates
**Fixed: "Table has no primary key. Cannot update." Error**

---

## 🐛 The Problem

Some tables in SQLite don't have explicit PRIMARY KEY columns defined. When you tried to edit cells in these tables, NestDB showed:

```
Error: Table has no primary key. Cannot update.
```

This happened because NestDB didn't know how to identify which specific row to update.

---

## ✅ The Solution

### How SQLite Works

**Every SQLite table has a hidden `rowid` column** - even if you don't define a PRIMARY KEY!

```sql
-- Table definition (no PRIMARY KEY)
CREATE TABLE test (
    name TEXT,
    value TEXT
);

-- But SQLite automatically adds a hidden rowid:
SELECT rowid, name, value FROM test;

-- Results:
-- rowid | name  | value
-- ------|-------|-------
-- 1     | test1 | val1
-- 2     | test2 | val2
```

The `rowid` is a unique integer that automatically increments for each row. It's perfect for identifying rows!

---

## 🔧 What I Fixed

### 1. Backend: Include `rowid` in Queries (`server/main.py`)

**Before:**
```python
query = f'SELECT * FROM "{table_name}" LIMIT ? OFFSET ?'
```

**After:**
```python
query = f'SELECT rowid, * FROM "{table_name}" LIMIT ? OFFSET ?'
```

Now every table's data includes the `rowid` column, even if it's not explicitly defined.

### 2. Frontend: Use `rowid` as Fallback (`labeller/templates/nestdb.html`)

**Before:**
```javascript
const pkColumns = tableSchema.filter(col => col.pk);

if (pkColumns.length === 0) {
    // Error: can't update!
    showToast('Error: Table has no primary key. Cannot update.', 'error');
    return;
}
```

**After:**
```javascript
const pkColumns = tableSchema.filter(col => col.pk);

if (pkColumns.length === 0) {
    // Use SQLite's built-in rowid instead!
    if (rowData.rowid === undefined) {
        showToast('Error: Cannot identify row (no primary key or rowid).', 'error');
        return;
    }
    rowId['rowid'] = rowData.rowid;
} else {
    // Use explicit primary key columns (normal case)
    pkColumns.forEach(col => {
        rowId[col.name] = rowData[col.name];
    });
}
```

Now NestDB automatically uses `rowid` for tables without explicit primary keys!

---

## 🚀 How to Test the Fix

### Step 1: Restart Backend

```bash
# Stop current backend (Ctrl+C)
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Create a Test Table (No Primary Key)

Go to **NestDB → SQL Editor** and run:

```sql
CREATE TABLE test_no_pk (
    name TEXT,
    value TEXT
);

INSERT INTO test_no_pk (name, value) VALUES ('test1', 'value1');
INSERT INTO test_no_pk (name, value) VALUES ('test2', 'value2');
INSERT INTO test_no_pk (name, value) VALUES ('test3', 'value3');
```

### Step 3: Try Editing

1. Go to **Table Browser** tab
2. Select the `test_no_pk` table
3. Toggle **"Edit Mode" ON**
4. Click on any cell and change the value
5. Press Enter to save

**Result:** ✅ It should work now! No more "no primary key" error.

### Step 4: Verify in Version History

1. Go to **Version Control** tab
2. See your update commit
3. Click **"Show Changes"** to see old → new value

---

## 📊 How It Works

### Example: Updating a Cell

**1. User edits a cell in table `test_no_pk`:**
```
Changed: value "value1" → "NEW_VALUE"
```

**2. Frontend checks for primary key:**
```javascript
// No explicit PRIMARY KEY in table
pkColumns.length === 0

// Fallback to rowid
rowId = { rowid: 1 }  // First row
```

**3. Backend receives update request:**
```json
{
  "table_name": "test_no_pk",
  "row_id": { "rowid": 1 },
  "updates": { "value": "NEW_VALUE" }
}
```

**4. Backend builds SQL query:**
```sql
-- Fetch old values (for change tracking)
SELECT rowid, * FROM "test_no_pk" WHERE "rowid" = 1

-- Update the row
UPDATE "test_no_pk" SET "value" = 'NEW_VALUE' WHERE "rowid" = 1
```

**5. Success!** ✅
- Change tracked in `bird_data_complete_changelog.db`
- Committed to Git version control
- User sees success toast

---

## 🎓 Educational Note: When Does SQLite Create `rowid`?

### Tables WITH `rowid` (99% of cases):
```sql
-- Regular table (no explicit PRIMARY KEY)
CREATE TABLE test (name TEXT);
-- Has hidden rowid: 1, 2, 3, ...

-- Table with non-INTEGER PRIMARY KEY
CREATE TABLE test2 (id TEXT PRIMARY KEY);
-- STILL has hidden rowid!

-- Table with INTEGER PRIMARY KEY
CREATE TABLE test3 (id INTEGER PRIMARY KEY);
-- rowid is aliased to "id" column
```

### Tables WITHOUT `rowid` (rare, must be explicit):
```sql
-- WITHOUT ROWID tables (advanced optimization)
CREATE TABLE test4 (id TEXT PRIMARY KEY) WITHOUT ROWID;
-- No rowid column at all
```

**Takeaway:** Almost all SQLite tables have `rowid`, so this fix works for 99%+ of cases!

---

## 🔍 Troubleshooting

### Problem: Still getting "no primary key" error after fix

**Solution:**
1. Make sure you **restarted the backend** after the code changes
2. **Refresh the browser** (Ctrl+Shift+R / Cmd+Shift+R)
3. Check browser console (F12) for JavaScript errors

### Problem: `rowid` column not showing in table view

**Normal!** The `rowid` column is there, but NestDB's table viewer might hide it. You can check it exists by running:

```sql
SELECT rowid, * FROM your_table LIMIT 5;
```

in the SQL Editor tab.

### Problem: Updates work but rollback buttons still missing

**Separate issue!** That's the Git commit hash linking problem. Follow these steps:

1. Restart backend (for Git hash linking fix)
2. Make a NEW database change (after restart)
3. Go to Version Control tab
4. Rollback buttons should appear on commits created AFTER the restart

---

## 📝 Summary

### What Changed:
1. ✅ **Backend includes `rowid`** in all SELECT queries
2. ✅ **Frontend uses `rowid`** for tables without explicit PRIMARY KEYs
3. ✅ **Updates work on ALL tables** (99%+ compatibility)

### Files Modified:
- `server/main.py` - Lines ~3058 and ~3172 (added `rowid` to SELECT queries)
- `labeller/templates/nestdb.html` - Lines ~1271-1280 (use `rowid` as fallback)

### Restart Required:
- ✅ **Backend:** Must restart for changes to take effect
- ❌ **Frontend:** Will automatically reload from backend

---

**Now you can edit ANY table in NestDB!** 🎉
