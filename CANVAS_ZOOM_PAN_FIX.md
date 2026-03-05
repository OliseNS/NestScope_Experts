# Canvas Zoom/Pan Implementation Plan

## Problems to Fix
1. No trackpad/mouse wheel zoom support
2. No pan/drag to navigate large images
3. Canvas doesn't feel like professional editing software (Photoshop, Figma, etc.)

## Professional Editing Software Standards

### Zoom Controls
- **Mouse Wheel**: Zoom in/out (Ctrl+Wheel for finer control)
- **Trackpad Pinch**: Native zoom gesture
- **Zoom to Cursor**: Zoom centers on cursor position
- **Keyboard**: `+`/`-` or `Ctrl +`/`Ctrl -`
- **Fit to Screen**: Reset zoom to fit image

### Pan Controls
- **Space + Drag**: Pan in any direction (universal standard)
- **Middle Mouse Drag**: Alternative pan method
- **Trackpad Drag**: Two-finger drag on Mac

### Visual Feedback
- Show zoom percentage in UI
- Cursor changes to hand icon when panning
- Smooth zoom transitions

## Implementation

### State Variables
```javascript
let panX = 0, panY = 0;  // Pan offset
let zoomLevel = 1.0;      // Current zoom (1.0 = 100%)
let isPanning = false;    // Panning active
let panStartX = 0, panStartY = 0;  // Pan start coords
let spacePressed = false; // Space key state
```

### Event Handlers
1. `handleWheel(e)` - Mouse wheel zoom
2. `handleKeyDown(e)` - Space key for pan mode
3. `handleKeyUp(e)` - Release space
4. `handleMouseDown(e)` - Start pan if space pressed
5. `handleMouseMove(e)` - Pan/draw based on mode
6. `handleMouseUp(e)` - End pan

### Coordinate Transformation
All canvas coordinates need transformation:
```javascript
function screenToCanvas(screenX, screenY) {
    return {
        x: (screenX - panX) / zoomLevel,
        y: (screenY - panY) / zoomLevel
    };
}

function canvasToScreen(canvasX, canvasY) {
    return {
        x: canvasX * zoomLevel + panX,
        y: canvasY * zoomLevel + panY
    };
}
```

### Zoom Implementation
```javascript
function zoomCanvas(delta, centerX, centerY) {
    const oldZoom = zoomLevel;

    // Exponential zoom for smooth scaling
    zoomLevel *= Math.pow(1.1, delta);
    zoomLevel = Math.max(0.1, Math.min(10, zoomLevel));

    // Adjust pan to keep cursor position fixed
    panX = centerX - (centerX - panX) * (zoomLevel / oldZoom);
    panY = centerY - (centerY - panY) * (zoomLevel / oldZoom);

    updateZoomDisplay();
    redrawCanvas();
}
```

### Pan Implementation
```javascript
function panCanvas(dx, dy) {
    panX += dx;
    panY += dy;
    redrawCanvas();
}
```

## Files to Modify
- `labeller/templates/expert_editor.html`
  - Add zoom/pan state variables
  - Add wheel event listener
  - Add keyboard event listeners
  - Update coordinate transformation functions
  - Update redrawCanvas() to apply zoom/pan
  - Add UI controls for zoom reset

## Testing Checklist
- [ ] Mouse wheel zooms in/out
- [ ] Zoom centers on cursor position
- [ ] Space + drag pans the canvas
- [ ] Zoom percentage updates in UI
- [ ] Drawing works correctly at any zoom level
- [ ] Edit mode works correctly at any zoom level
- [ ] Segment tool works correctly at any zoom level
- [ ] Reset zoom button works
- [ ] Keyboard shortcuts work (+/- for zoom)
