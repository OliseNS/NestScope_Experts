# Custom Modal System - Expert Editor

All browser native alerts and confirms have been replaced with beautiful custom modals.

## ✅ Universal Modal System

### Custom Alert Function
```javascript
showCustomAlert(title, message, icon, iconColor)
```
**Usage:**
- Image loading errors
- Classification failures
- Invalid inputs
- Success messages
- Info messages

**Example:**
```javascript
showCustomAlert(
    'Image Loading Error',
    'Failed to load <strong>image.jpg</strong>',
    '❌',
    '#dc2626'
);
```

### Custom Confirm Function
```javascript
showCustomConfirm(title, message, icon, iconColor, confirmText, cancelText, danger)
```
**Usage:**
- Unsaved changes warnings
- Delete confirmations
- Irreversible actions

**Example:**
```javascript
const confirmed = await showCustomConfirm(
    'Unsaved Changes',
    'You have unsaved changes. Are you sure?',
    '⚠️',
    'var(--orange-primary)',
    'Leave Anyway',
    'Cancel',
    true
);
```

## 🎨 Specialized Modals

### 1. Delete Image Modal
**ID:** `delete-confirm-modal`
**Trigger:** Shift+Delete key or Delete button
**Functions:**
- `showDeleteConfirm()` - Opens modal
- `hideDeleteConfirm()` - Closes modal
- `confirmDelete()` - Executes deletion

**Features:**
- Warning emoji and red accent color
- Image name highlighted
- Irreversible action warning
- Custom styled buttons

### 2. Delete All Boxes Modal
**ID:** `delete-all-modal`
**Trigger:** Delete All button click
**Functions:**
- `showDeleteAllConfirm()` - Opens modal
- `hideDeleteAllConfirm()` - Closes modal
- `confirmDeleteAll()` - Deletes all boxes

**Features:**
- Trash icon with red accent
- Dynamic box count display
- Undo support
- Toast notification on success

### 3. AI Detection Mode Modal
**ID:** `aiDetectionModal`
**Trigger:** "S" key press
**Functions:**
- `showAIDetectionModal()` - Opens modal
- `closeAIDetectionModal(confirmed, sliceSize)` - Closes and executes

**Features:**
- Two detection mode buttons:
  - Standard SAHI (1024×1024)
  - SuperZoom (512×512)
- Visual icons for each mode
- Speed vs accuracy descriptions

### 4. Add Species Class Modal
**ID:** `add-class-modal`
**Trigger:** Manual add class action
**Functions:**
- `showAddClassDialog()` - Opens modal
- `hideAddClassDialog()` - Closes modal
- `addNewClass()` - Creates new species entry

## 🎯 Replaced Browser Dialogs

All instances replaced:

### Alert() Replacements
1. ✅ Image loading error (line ~1575)
2. ✅ No birds to classify (line ~2904)
3. ✅ Classification failed (line ~2986)
4. ✅ Invalid image number (line ~4157)
5. ✅ Image deleted success (line ~4316)
6. ✅ Delete image error (line ~4319)
7. ✅ Server connection failed (line ~4323)

### Confirm() Replacements
1. ✅ Unsaved changes warning (line ~4268)
2. ✅ Delete image permanently (line ~4286)
3. ✅ Delete all boxes (line ~4479)

## 🎨 Design Features

### Visual Consistency
- **Background:** `rgba(0,0,0,0.7)` with `backdrop-filter: blur(4px)`
- **Surface:** `var(--surface)` with coastal border
- **Border Radius:** 16px for modern look
- **Z-Index:** 20000 (above all other elements)

### Icon System
- 64px circular icon containers
- Emoji or Lucide icons
- Color-coded backgrounds (success, error, warning, info)

### Button Styles
- **Primary:** Orange gradient (`var(--orange-primary)`)
- **Danger:** Red (`#dc2626`)
- **Secondary:** Light surface with border
- Hover effects and transitions

### Typography
- **Title:** Serif font, 1.5rem
- **Message:** Secondary text color, line-height 1.6
- **Supports HTML:** Can use `<strong>`, `<br>`, etc.

## 🔧 Technical Implementation

### Promise-Based
All custom modals return Promises for async/await support:
```javascript
const result = await showCustomConfirm('Title', 'Message');
if (result) {
    // User confirmed
}
```

### Dismissable
Modals can be closed by:
- Clicking outside (if `universalModalDismissable` is true)
- Clicking Cancel button
- Pressing Escape key (future enhancement)

### State Management
```javascript
window.universalModalCallback = null;  // Stores Promise resolver
window.universalModalDismissable = true;  // Controls outside click
```

## 📱 Mobile Responsive

All modals are responsive:
- **Width:** 90% with max-width 480px
- **Padding:** Scaled for touch targets
- **Font Size:** Readable on small screens
- **Button Size:** 44px+ tap targets

## 🎭 Theme Integration

Modals automatically inherit theme variables:
- `--surface` - Modal background
- `--text-primary` - Headings
- `--text-secondary` - Body text
- `--orange-primary` - Accent color
- `--surface-light` - Secondary buttons

Dark mode automatically applies through CSS variables.

## ✨ Best Practices

### When to use showCustomAlert()
- Single-button informational messages
- Error messages that don't require action
- Success confirmations
- Warnings that are informational only

### When to use showCustomConfirm()
- User needs to make a choice
- Irreversible actions (set `danger: true`)
- Actions that might lose data
- Navigation with unsaved changes

### When to create specialized modals
- Complex UI (multiple options, forms)
- Reusable across multiple actions
- Specific branded styling needed
- Multi-step workflows

## 🚀 Future Enhancements

Potential improvements:
- Keyboard shortcuts (Escape to close, Enter to confirm)
- Animation on open/close
- Stack multiple modals
- Input field support in universal modal
- Loading state indicator
- Progress bars for long operations
