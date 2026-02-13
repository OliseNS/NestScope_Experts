# NestVision Correction Workflow - UPDATED

## How It Works (Simplified)

The correction feature now integrates seamlessly with the existing labeller, using all its powerful tools!

### Workflow

1. **Detect Birds in NestVision**
   - Upload an image in the NestVision tab
   - Run AI detection
   - Review the results

2. **Click "Correct AI" Button**
   - Image is uploaded to labeller
   - Saved as `correction_{timestamp}.jpg` in `labeller/nestvision/images/`
   - AI detections converted to YOLO labels in `labeller/nestvision/labels/`
   - Added to project_state.json under "Corrections" user
   - **Automatically opens the regular labeller editor**

3. **Use Full Labeller Tools**
   The regular labeller page opens with:
   - ✅ All the toolbar tools (Box, SAM segmentation, etc.)
   - ✅ Class selection on the left
   - ✅ Keyboard shortcuts
   - ✅ Pan and zoom
   - ✅ MobileSAM integration
   - ✅ Save/Next/Previous navigation

4. **Make Corrections**
   - Fix wrong bounding boxes
   - Change classes
   - Add missing birds
   - Delete false positives
   - Use SAM tool for precise segmentation

5. **Save & Continue**
   - Click "Save & Next" in labeller
   - Corrections saved to `labeller/nestvision/labels/`
   - Move to next image or close

## Benefits of This Approach

✅ **No Duplicate Tools** - Uses existing, tested labeller UI
✅ **Full Feature Set** - All labelling tools available
✅ **Consistent Experience** - Same UI for corrections and regular labelling
✅ **Easier Maintenance** - One codebase for labelling
✅ **Project State Integration** - Corrections tracked in project state

## File Structure

```
labeller/
├── nestvision/
│   ├── images/
│   │   ├── regular_images.jpg
│   │   └── correction_1234567890.jpg  # Correction images
│   ├── labels/
│   │   ├── regular_images.txt
│   │   └── correction_1234567890.txt  # Correction labels
│   └── crops/                          # Species-identified crops
└── project_state.json                  # Tracks assignments
```

## Project State Structure

```json
{
  "classes": ["bird"],
  "assignments": {
    "User_1": {
      "images": ["img1.jpg", "img2.jpg"],
      "completed": ["img1.jpg"]
    },
    "Corrections": {
      "images": ["correction_1234567890.jpg"],
      "completed": []
    }
  }
}
```

## Access Corrections User

You can always go back to correct more images:

1. Go to http://localhost:5000
2. Click on "Corrections" user
3. All correction images will be listed
4. Edit any image again

## Migration from Old Approach

If you were using the old separate correction system:
- Old path: `labeller/nestvision/corrections/images/`
- New path: `labeller/nestvision/images/`
- Files now have `correction_` prefix instead of hash names
- Integrated in project_state.json for better tracking

## Technical Details

### Image Upload Process

1. Frontend sends image + detections to `/api/correction/upload`
2. Backend:
   - Decodes base64 image
   - Generates filename: `correction_{timestamp}.jpg`
   - Saves to `labeller/nestvision/images/`
   - Converts detections to YOLO format
   - Saves labels to `labeller/nestvision/labels/`
   - Updates project_state.json
   - Returns URL: `/editor/Corrections`
3. Frontend opens labeller in new tab

### Auto-Open Implementation

Uses JavaScript to open new tab:
```javascript
window.open('http://localhost:5000/editor/Corrections', '_blank');
```

If popup is blocked, provides fallback link.

## Tips

- **Corrections User**: All correction images go to this special user
- **Filename Format**: `correction_{millisecond_timestamp}.jpg` ensures uniqueness
- **Full Tools**: You get the exact same tools as regular labelling
- **Easy to Find**: Look for images starting with "correction_" in the labeller
- **Batch Corrections**: Upload multiple images - they all go to Corrections user

## Troubleshooting

### Labeller page doesn't open
- Check if labeller is running: `curl http://localhost:5000`
- Check browser popup blocker settings
- Use the fallback link provided

### Image not in labeller
- Check `labeller/nestvision/images/` for correction_*.jpg files
- Check project_state.json for "Corrections" user
- Restart labeller: `python labeller/app.py --data nestvision`

### Can't see correction images
- Go to http://localhost:5000
- Look for "Corrections" in the user list
- Click on it to see all correction images

## Future Enhancements

Possible improvements:
- [ ] Mark corrections differently in the UI
- [ ] Track correction history
- [ ] Compare original vs corrected
- [ ] Merge corrections back to training dataset with one click
- [ ] Correction statistics and quality metrics
