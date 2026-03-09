# Fast Image Deletion Update

## Changes Made (2026-03-09)

### Problem
When purging large numbers of bad/low-quality images:
- Had to click delete button for each image
- Confirmation dialog slowed down workflow
- No keyboard shortcut available

### Solution ✅

Implemented **fast deletion workflow** optimized for quickly purging bad images:

1. **Keyboard Shortcut**: `Shift+Delete`
2. **No Confirmation Dialog**: Instant deletion
3. **Faster Navigation**: 500ms delay instead of 1000ms
4. **Visual Feedback**: Toast notifications with color coding

---

## Features

### 1. Keyboard Shortcut: Shift+Delete

**Usage**:
- Press `Shift+Delete` to instantly delete current image
- Works from anywhere in the editor (no need to click button)
- Prioritized over box deletion (Delete alone still deletes boxes)

**Why Shift+Delete?**
- Standard for permanent deletion in many apps
- Requires two keys to prevent accidental deletion
- Easy to spam for fast purging: Shift+Delete → Shift+Delete → Shift+Delete

### 2. No Confirmation Dialog

**Before**:
```
Click Delete → Confirmation popup → Click OK → Wait 1s → Navigate
```

**After**:
```
Shift+Delete → Wait 0.5s → Navigate
```

**Time saved**: ~2-3 seconds per image

For 50 bad images: **Saves 100-150 seconds** (2-3 minutes)

### 3. Faster Navigation

Auto-navigates to next image after **500ms** (was 1000ms)

- Quick enough to see deletion confirmation
- Fast enough for rapid purging workflow
- Shows toast: "✓ Deleted: filename.jpg"

### 4. Color-Coded Toasts

Updated `showToast()` function to accept type parameter:

```javascript
showToast('Message', 'success')  // Green border
showToast('Message', 'error')    // Red border
showToast('Message', 'info')     // Orange border (default)
showToast('Message', 'warning')  // Yellow border
```

**Deletion flow toasts**:
1. `🗑️ Deleting image...` (blue/info)
2. `✓ Deleted: filename.jpg` (green/success)
3. OR `❌ Delete failed: error` (red/error)

---

## Keyboard Shortcuts Reference

Updated shortcuts list in canvas overlay:

| Shortcut | Action |
|----------|--------|
| **Wheel** | Zoom to cursor |
| **H or Space+Drag** | Pan canvas |
| **Delete** | Remove selected box |
| **Shift+Delete** | Delete current image |
| **Ctrl+S** | Save & next image |

---

## Workflow: Fast Purging

**Scenario**: You have 100 images, 20 are bad quality, need to remove them.

**Old Workflow** (per image):
1. Look at image (assess quality)
2. Move mouse to delete button
3. Click button
4. Read confirmation dialog
5. Click "OK"
6. Wait 1 second
7. Next image loads

**Time**: ~5-7 seconds per image × 20 = **100-140 seconds** (1.5-2.3 minutes)

**New Workflow** (per image):
1. Look at image (assess quality)
2. Press `Shift+Delete`
3. Next image loads (0.5s)

**Time**: ~1-2 seconds per image × 20 = **20-40 seconds**

**Time saved**: ~80-100 seconds for 20 images

---

## Safety Considerations

### "Why no confirmation for permanent deletion?"

**Design Philosophy**: Optimized for expert users doing bulk operations

**Safety Measures**:
1. **Shift+Delete** requires two keys (prevents accidental press)
2. **Toast notification** confirms what was deleted
3. **Git/backups** should be used for important datasets
4. **Labels deleted too** - full cleanup
5. **User must hold Shift** - can't rapid-fire by accident

### "What if I accidentally delete?"

**Recovery options**:
1. **Project export** before purging (YOLO format includes all files)
2. **Git version control** (commit before major purges)
3. **Manual backup** of images folder
4. **Project state file** tracks what was assigned (can audit deletions)

**Best Practice**:
```bash
# Before major purge, export project
cd /projects/stage_2
zip -r backup_before_purge.zip images/ labels/ project_state.json

# Then purge with confidence
# Press Shift+Delete repeatedly on bad images
```

---

## Technical Details

### Files Modified

1. **labeller/templates/expert_editor.html**
   - Line 737-741: Updated delete button tooltip
   - Line 2951-2989: Removed confirmation, faster navigation
   - Line 3039-3048: Added Shift+Delete handler
   - Line 750: Added Shift+Delete to shortcuts help
   - Line 2843-2861: Added type parameter to showToast()

### Code Changes

**Keyboard Handler**:
```javascript
// Delete current image: Shift+Delete (fast purging workflow)
if (e.key === 'Delete' && e.shiftKey) {
    e.preventDefault();
    deleteCurrentImage();
    return; // Don't process as box deletion
}

// Delete selected box: Delete or Backspace (only if box is selected)
if ((e.key === 'Delete' || e.key === 'Backspace') && selectedBoxId && !e.shiftKey) {
    e.preventDefault();
    deleteBoxQuick(selectedBoxId);
}
```

**Key points**:
- `Shift+Delete` checked FIRST (higher priority)
- Returns immediately to prevent fallthrough
- Box deletion only works if no Shift key

**Delete Function**:
```javascript
async function deleteCurrentImage() {
    // No confirmation dialog
    showToast('🗑️ Deleting image...', 'info');

    const response = await fetch('/api/delete_image', { /* ... */ });

    if (result.success) {
        showToast('✓ Deleted: ' + IMAGE_NAME, 'success');

        // Fast navigation (500ms instead of 1000ms)
        setTimeout(() => {
            window.location.href = `/project/${PROJECT_ID}/editor/${USERNAME}/${NEXT_INDEX}`;
        }, 500);
    }
}
```

---

## Use Cases

### 1. Initial Dataset Curation
Upload 500 raw images → quickly scan through → delete corrupted/blurry ones → keep only good quality

**Workflow**:
- Open first image
- If bad: `Shift+Delete`
- If good: `→` (next arrow) or `Ctrl+S` (save empty)
- Repeat

### 2. Post-Annotation Cleanup
Found some poorly annotated images → delete them → reassign better images

### 3. Duplicate Removal
Imported dataset has duplicates → quickly delete them as you see them

### 4. Quality Control
Expert reviews dataset → marks bad images for deletion → uses fast purge

---

## Testing Checklist

- [x] `Shift+Delete` deletes current image
- [x] No confirmation dialog shown
- [x] Toast shows deletion in progress
- [x] Toast shows success message
- [x] Navigates to next image after 500ms
- [x] Falls back to previous if no next
- [x] Falls back to dashboard if no images left
- [x] `Delete` alone still deletes boxes (not image)
- [x] Shortcuts help updated with Shift+Delete
- [x] Button tooltip updated
- [x] Toast colors work (success/error/info)
- [ ] Test with 50+ image purge
- [ ] Test keyboard shortcut doesn't conflict with other shortcuts
- [ ] Test on different browsers

---

## User Feedback Integration

Based on user request:
> "Add a shortcut for deleting and make it not ask me 2 times for deleting it. I have a lot of bad images i need to purge sometimes"

**Implemented**:
- ✅ Keyboard shortcut added (`Shift+Delete`)
- ✅ Confirmation removed (no asking)
- ✅ Optimized for bulk purging workflow
- ✅ Fast navigation (500ms)

**Result**: User can now purge bad images at ~1-2 seconds per image instead of 5-7 seconds.

---

## Future Enhancements

Possible improvements based on this workflow:

- [ ] **Batch delete mode**: Select multiple images → delete all at once
- [ ] **Delete and mark reason**: Tag deleted images (blurry/duplicate/wrong species)
- [ ] **Undo last delete**: Keep deleted images in trash folder for 24h
- [ ] **Delete counter**: Show "Deleted 5 images this session"
- [ ] **Delete hotkey customization**: Let users choose their own shortcut
- [ ] **Preview next image**: Show thumbnail of next image before deleting
- [ ] **Smart suggestions**: Auto-flag potentially bad images (blur detection)

---

## Rollback Instructions

If users prefer the old confirmation dialog:

1. Open `labeller/templates/expert_editor.html`
2. Find `async function deleteCurrentImage()` (around line 2951)
3. Add confirmation back at the start:
```javascript
async function deleteCurrentImage() {
    // Add this back:
    const confirmed = confirm(
        `⚠️ Delete "${IMAGE_NAME}"?\n\n` +
        `This will permanently remove the image and its labels.`
    );
    if (!confirmed) return;

    // Rest of function...
}
```

4. Or disable keyboard shortcut by commenting out lines 3039-3043

---

## Performance Impact

**Minimal**:
- No additional API calls
- Same backend deletion logic
- Slightly faster navigation (500ms vs 1000ms)
- Toast notifications are lightweight

**Network**: Same as before (1 DELETE request per image)

**Memory**: No change

---

## Accessibility Notes

**Keyboard-only users**:
- ✅ Can delete without mouse (Shift+Delete)
- ✅ All operations remain keyboard-accessible
- ✅ Shortcuts help text updated

**Screen readers**:
- Toast notifications should be announced
- Button aria-label includes shortcut: "Delete low-quality image (Shift+Delete)"

**Power users**:
- Can keep hands on keyboard entire time
- No need to reach for mouse to click delete button
- Muscle memory: Shift+Delete → Shift+Delete → Shift+Delete

---

## Educational Note

### Why remove confirmation dialogs?

**Context matters!**

**When confirmations are good**:
- Irreversible system actions (format drive, delete account)
- Inexperienced users
- Rare actions (most users never encounter)

**When confirmations are bad**:
- Expert users doing repetitive tasks
- Workflow disruption (breaks flow state)
- False sense of security ("I clicked OK without reading")

**Our case**: Expert annotators purging bad images
- Know what they're doing
- Doing it repeatedly (50+ times)
- Can recover from backups if needed
- Speed > safety prompts

**Design principle**: Trust the expert user, optimize for their workflow.

Similar examples:
- Vim's `:wq!` (force quit without save) - no confirmation
- Photoshop's merge layers - no confirmation
- Git's `git reset --hard` - no confirmation

All are **dangerous** but **frequently used by experts** who know the risks.
