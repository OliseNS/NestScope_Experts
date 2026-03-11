# Excel-Like NestDB Guide
**Making Database Management as Easy as Excel**

---

## 🎯 What's New

NestDB now works just like Excel! No more popup forms - add rows and columns directly in the table with inline editing.

---

## 📊 Adding Rows (Like Excel)

### Method 1: Click "+ Add New Row" Button

1. **Open a table** in Table Browser
2. **Scroll to the bottom** of the table
3. Click the **"+ Add New Row"** button
4. A new row appears with input fields for each column
5. **Type your values** (Tab to move between fields, Enter to save)
6. Press **Enter** on the last field to save, or click the **✓** button

### Method 2: Click "+ Add First Row" (Empty Table)

If the table is empty:
1. Click **"+ Add First Row"** button in the center
2. New row appears with input fields
3. Fill in values and press Enter to save

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Enter** | Move to next field or save (if on last field) |
| **Tab** | Move to next field |
| **Shift+Tab** | Move to previous field |
| **Esc** | Cancel (discard new row) |

### Visual Feedback

- **Green highlight:** New row being edited
- **"NEW" label:** Shows which row is new
- **Green border:** Input fields have green border
- **Red asterisk (*):** Required fields

### Example Workflow

```
1. Click "+ Add New Row" at bottom of table
2. Type: "test_name" [Tab]
3. Type: "test_value" [Tab]
4. Type: "12345" [Enter]
5. ✓ Row saved and committed!
```

---

## 📋 Adding Columns (Like Excel)

### Step 1: Click "+ Column" Button

In the table header (right side), click the **"+ Column"** button

### Step 2: Enter Column Name

A dialog appears:
```
Enter new column name: ___________
```

**Rules:**
- Must start with letter or underscore
- Can contain letters, numbers, underscores
- Examples: `price`, `user_email`, `created_at`

### Step 3: Choose Column Type

```
Enter column type (TEXT, INTEGER, REAL, BLOB): _______
```

**Common Types:**
- `TEXT` - For strings (names, descriptions, URLs)
- `INTEGER` - For whole numbers (counts, IDs, years)
- `REAL` - For decimals (prices, measurements, percentages)
- `BLOB` - For binary data (rare)

### Step 4: Allow NULL?

```
Allow NULL values?  [Yes] [No]
```

- **Yes** - Column can be empty
- **No** - Column must always have a value (requires default)

### Result

✓ Column added to table!
- New column appears on the right
- Existing rows have NULL (or default value)
- Can immediately start editing values

---

## ✕ Deleting Rows

Each row has a small **✕** button next to the row number:

1. **Click the ✕** button on any row
2. **Confirm deletion** in the dialog
3. Row is deleted and change is committed

**Note:** This action is tracked in version control, so you can rollback if needed!

---

## ✕ Deleting Columns

Each column header has a small **✕** button:

1. **Click the ✕** button on any column header
2. **Confirm deletion** in the dialog

**Note:** SQLite doesn't support DROP COLUMN directly, so this requires complex migration. For now, use the SQL Editor for column deletion.

---

## 🔄 Comparison: Old vs. New

### Old Way (Modal Popup)

```
1. Click "Insert Row" button
2. Popup appears with form
3. Fill out each field in form
4. Click "Insert Row" button
5. Popup closes
6. Table refreshes
```

❌ **Annoying:** Context switch, many clicks, breaks flow

### New Way (Inline Editing)

```
1. Click "+ Add New Row"
2. Type directly in table
3. Press Enter
```

✅ **Excel-like:** Fast, intuitive, stays in context

---

## 💡 Pro Tips

### Tip 1: Batch Row Entry

You can quickly add multiple rows:

```
1. Click "+ Add New Row"
2. Fill in row 1, press Enter
3. Repeat!
```

The "Add New Row" button reappears after each save.

### Tip 2: Required Fields First

Plan your column order so required fields come first. This makes data entry faster (you don't have to skip optional fields).

### Tip 3: Use Tab for Speed

Don't use the mouse! Type value → Tab → Type value → Tab → Enter

### Tip 4: Esc to Cancel

Made a mistake? Press **Esc** to cancel without saving.

### Tip 5: Check Version History

Every row addition/deletion is committed to Git. Go to **Version Control** tab to see:
- What changed
- Who changed it
- When it changed
- Rollback if needed

---

## 🎨 Visual Guide

### Adding a Row

```
┌─────┬───────────┬──────────────┬────────┐
│  #  │   name    │    value     │ action │
├─────┼───────────┼──────────────┼────────┤
│  1  │   test1   │    val1      │        │
│  2  │   test2   │    val2      │        │
│  3  │   test3   │    val3      │        │
└─────┴───────────┴──────────────┴────────┘
                 ▼ Click here
┌───────────────────────────────────────────┐
│      + Add New Row                        │
└───────────────────────────────────────────┘
                 ▼ Becomes
┌─────┬──────────────┬──────────────┬────────┐
│ NEW │ [name*]      │ [value*]     │ ✓ ✕   │  ← Type here
└─────┴──────────────┴──────────────┴────────┘
```

### Adding a Column

```
┌─────┬───────────┬──────────────┬────────────┐
│  #  │   name    │    value     │ + Column   │  ← Click here
└─────┴───────────┴──────────────┴────────────┘

Dialog appears:
┌────────────────────────────────────┐
│ Enter new column name:             │
│ ▸ price                            │
│                                    │
│ Enter column type:                 │
│ ▸ REAL                             │
│                                    │
│ Allow NULL values? [Yes] [No]      │
└────────────────────────────────────┘

Result:
┌─────┬───────────┬──────────────┬────────┬────────────┐
│  #  │   name    │    value     │ price  │ + Column   │
├─────┼───────────┼──────────────┼────────┼────────────┤
│  1  │   test1   │    val1      │  NULL  │            │
│  2  │   test2   │    val2      │  NULL  │            │
└─────┴───────────┴──────────────┴────────┴────────────┘
```

---

## 🚨 Error Messages

### "Finish editing the current row first"

**Cause:** You tried to add another row while still editing one.

**Solution:** Press Enter to save current row, or Esc to cancel it.

### "Error: [column] is required"

**Cause:** You left a required field empty.

**Solution:** Fill in all fields marked with red asterisk (*).

### "Invalid column name"

**Cause:** Column name contains spaces or special characters.

**Solution:** Use only letters, numbers, underscores (e.g., `user_name` not `user name`).

---

## 📖 Examples

### Example 1: Creating a Simple Contact List

**Step 1:** Create table (SQL Editor)
```sql
CREATE TABLE contacts (
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT
);
```

**Step 2:** Add rows (Excel-like)
```
Click "+ Add First Row"
Enter: "John Doe" [Tab] "john@example.com" [Tab] "555-1234" [Enter]
✓ Row saved!

Click "+ Add New Row"
Enter: "Jane Smith" [Tab] "jane@example.com" [Tab] "555-5678" [Enter]
✓ Row saved!
```

**Step 3:** Add column for notes
```
Click "+ Column"
Name: "notes"
Type: "TEXT"
Allow NULL: Yes
✓ Column added!
```

---

### Example 2: Product Inventory

**Step 1:** Create table
```sql
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0
);
```

**Step 2:** Add products
```
Click "+ Add First Row"
[Skip product_id - auto-increment]
Enter: "Widget" [Tab] "19.99" [Tab] "100" [Enter]

Click "+ Add New Row"
Enter: "Gadget" [Tab] "29.99" [Tab] "50" [Enter]
```

---

## 🔍 Troubleshooting

### Problem: "+ Add New Row" button not appearing

**Solution:**
1. Make sure you've selected a table
2. Check if you're already editing a row (press Esc to cancel)
3. Refresh the table (click Refresh button)

### Problem: Can't Tab between fields

**Solution:** Use arrow keys or click with mouse. Tab works but may behave differently in different browsers.

### Problem: Enter key doesn't save

**Solution:** Make sure you're on the last field. If not on last field, Enter moves to next field.

---

## 🎓 Why Excel-Like Is Better

### Traditional Database Tools

```
phpMyAdmin: Click "Insert" → Popup form → Fill 10 fields → Click "Go" → Close popup
pgAdmin: Right-click → "Add Row" → Form opens → Fill fields → Save → Close
```

### NestDB (Excel-Like)

```
Click once → Type → Press Enter
```

**Result:** 10x faster data entry! 🚀

---

## 🔐 Safety Features

### All Changes Are Tracked

Every row/column addition is:
- ✅ Committed to Git version control
- ✅ Tracked with user attribution (your email)
- ✅ Timestamped
- ✅ Rollback-able

### Confirmation for Destructive Actions

- ✅ Deleting rows requires confirmation
- ✅ Deleting columns requires confirmation
- ✅ Can't accidentally delete data

### Esc to Cancel

- ✅ Press Esc anytime to cancel new row
- ✅ No data saved until you explicitly press Enter or click ✓

---

## 📊 Comparison Chart

| Feature | Old Modal | New Excel-Like |
|---------|-----------|----------------|
| Add Row | 5 clicks | 1 click + typing |
| Visibility | Popup blocks view | Inline in table |
| Keyboard Nav | Limited | Full Tab/Enter support |
| Batch Entry | Slow (popup each time) | Fast (inline flow) |
| Cancel | Click Cancel button | Press Esc |
| Learning Curve | Medium | Low (like Excel) |

---

## 🚀 Next Steps

Now that you know the Excel-like features:

1. **Try adding a row** - Click "+ Add New Row" and experiment
2. **Try adding a column** - Click "+ Column" and create a new field
3. **Check Version History** - See your changes tracked in Git
4. **Try rollback** - Go back if you make a mistake

**Happy data entry!** 📊✨
