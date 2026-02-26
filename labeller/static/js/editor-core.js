/**
 * Nestperts Editor Core JavaScript
 *
 * This file contains all the core logic for the Nestperts labelling interface.
 * It expects the following global variables to be defined before this script loads:
 * - USERNAME: string - current user's name (from Flask template)
 * - INITIAL_CLASSES: array - list of class names (from Flask template)
 * - INITIAL_SPECIES: array - list of species objects (from Flask template)
 */

// Color palette for bounding boxes
const COLORS = [
    '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#00FFFF', '#FF00FF',
    '#FFA500', '#800080', '#008080', '#FFC0CB', '#FFD700', '#C0C0C0'
];

// --- STATE ---
let appState = {
    classes: INITIAL_CLASSES,
    speciesList: INITIAL_SPECIES,
    currentImage: null,
    currentIndex: 0,
    totalImages: 0,
    labels: [], // {class_id, x, y, w, h, species} (normalized 0-1)

    selectedClassId: 0,
    selectedLabelIndex: -1,

    // Canvas Transform
    scale: 1,
    panX: 0,
    panY: 0,

    // Tools
    tool: 'draw', // 'draw', 'sam' (AI detect), 'edit', 'pan'
    isSpaceHeld: false, // For temporary pan
    samProcessing: false, // AI detection is running (DEPRECATED - now tracks per-point)
    samPoints: [], // Collected points for AI detection {x, y, processing: bool, pointIndex: int} in world coordinates
    samAnimationFrame: null, // Animation frame ID for glowing effect

    // Interaction State
    mode: 'IDLE', // IDLE, DRAWING, DRAGGING_VIEW, RESIZING, MOVING

    // Temp variables for interaction
    startX: 0,
    startY: 0,
    resizeHandle: null // 'tl', 'tr', 'bl', 'br'
};

const canvas = document.getElementById('editor');
const ctx = canvas.getContext('2d');
const imgObj = new Image();

// --- TAB SWITCHING ---

/**
 * Switch between Draw and Classify tabs.
 *
 * This function handles the UI state for tab navigation. When switching to
 * the Classify tab, it will load and render the bbox list. The Draw tab
 * contains all the drawing tools and class selectors.
 *
 * @param {string} tabName - Either 'draw' or 'classify'
 */
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.remove('active');
        el.style.display = 'none';
    });

    // Hide all tab buttons active state
    document.querySelectorAll('.tab-btn').forEach(el => {
        el.classList.remove('active');
    });

    // Show selected tab
    const tabContent = document.getElementById('tab-' + tabName);
    if (tabContent) {
        tabContent.classList.add('active');
        tabContent.style.display = 'flex';
    }

    // Activate selected button
    const tabBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    if (tabBtn) {
        tabBtn.classList.add('active');
    }

    // Tab-specific actions
    if (tabName === 'classify') {
        // When switching to classify tab, render the bbox list
        renderBBoxList();
    }

    console.log(`Switched to ${tabName} tab`);
}

/**
 * Render the bounding box list in the Classify tab.
 *
 * This function will be fully implemented in Phase 4. For now, it's a stub
 * that shows a placeholder message.
 */
function renderBBoxList() {
    const bboxList = document.getElementById('bbox-list');
    const bboxCount = document.getElementById('bbox-count');

    if (!bboxList || !bboxCount) return;

    // Update count
    bboxCount.textContent = appState.labels.length;

    // Stub implementation - will be replaced in Phase 4
    if (appState.labels.length === 0) {
        bboxList.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">No bounding boxes yet. Switch to Draw Boxes tab to add some!</p>';
    } else {
        bboxList.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">Classification UI coming in Phase 4...</p>';
    }
}

// Helper to get parent div size
const getContainerSize = () => {
    const d = canvas.parentElement;
    return { w: d.clientWidth, h: d.clientHeight };
};

// --- INITIALIZATION ---
function init() {
    renderClassList();
    renderSpeciesList();

    // Initial Resize
    resizeCanvas();
    loadImage();

    // Check SAM status
    checkSAMStatus();

    // Events
    window.addEventListener('resize', resizeCanvas);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    canvas.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    canvas.addEventListener('wheel', onWheel, { passive: false });
    canvas.addEventListener('contextmenu', e => e.preventDefault());

    imgObj.onload = () => {
        resizeCanvas();
        resetView();
        draw();
    };

    imgObj.onerror = () => {
        console.error('Failed to load image:', imgObj.src);
        alert('Failed to load image. Please check that the image file exists and is accessible.');
        hideLoader();
    };
}

function setTool(tool) {
    appState.tool = tool;
    document.getElementById('btn-draw').className = `tool-btn ${tool === 'draw' ? 'active' : ''}`;
    document.getElementById('btn-sam').className = `tool-btn ${tool === 'sam' ? 'active' : ''}`;
    document.getElementById('btn-edit').className = `tool-btn ${tool === 'edit' ? 'active' : ''}`;
    document.getElementById('btn-pan').className = `tool-btn ${tool === 'pan' ? 'active' : ''}`;

    // Cursor updates
    updateCursor();

    // If switching to draw/pan/sam, deselect
    if (tool !== 'edit') {
        appState.selectedLabelIndex = -1;
    }

    // Clear detection points when switching away from AI detect mode
    if (tool !== 'sam') {
        appState.samPoints = [];
    }

    draw();
}

function updateCursor() {
    if (appState.isSpaceHeld || appState.tool === 'pan') {
        canvas.style.cursor = appState.mode === 'DRAGGING_VIEW' ? 'grabbing' : 'grab';
    } else if (appState.tool === 'draw') {
        canvas.style.cursor = 'crosshair';
    } else if (appState.tool === 'sam') {
        canvas.style.cursor = 'pointer'; // Always pointer in SAM mode (non-blocking)
    } else if (appState.tool === 'edit') {
        canvas.style.cursor = 'default';
    }
}

// --- COORDINATE HELPERS ---

function clamp(val, min, max) {
    return Math.min(Math.max(val, min), max);
}

function toWorld(sx, sy) {
    return {
        x: (sx - appState.panX) / appState.scale,
        y: (sy - appState.panY) / appState.scale
    };
}

function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}

// --- API CALLS ---

async function checkSAMStatus() {
    try {
        const res = await fetch('/api/sam_status');
        const data = await res.json();

        if (data.status === 'ready') {
            console.log(`🤖 ${data.model} ready on ${data.device.toUpperCase()}`, data);

            // Inform about performance
            if (data.device === 'cpu') {
                console.log('ℹ️ Using CPU - detection takes 1-3s per point');
                console.log('💡 GPU available? Detection would be <1s per point');
            } else {
                console.log('⚡ Using GPU - ultra-fast detection (<1s per bird)!');
            }
        }
    } catch (e) {
        console.error('Failed to check detection model status:', e);
    }
}

async function loadImage(index = null) {
    showLoader('Fetching image...');
    try {
        let url = `/api/get_image/${USERNAME}?t=${Date.now()}`;
        if (index !== null) url += `&index=${index}`;

        const res = await fetch(url);
        const data = await res.json();

        if (data.done || data.error) {
            alert("Great job! All images completed or no images found.");
            window.location.href = '/';
            return;
        }

        appState.currentImage = data.image;
        appState.currentIndex = data.index;
        appState.totalImages = data.total;

        document.getElementById('progress-text').innerText = `${data.index + 1} / ${data.total}`;
        document.getElementById('global-progress').innerText = `Completed: ${data.progress}`;

        // Handle disabling/enabling of nav buttons
        const prevBtn = document.querySelector('.nav-btn[title="Previous Image"]');
        const nextBtn = document.querySelector('.nav-btn[title="Next Image"]');
        if (prevBtn) prevBtn.disabled = data.index === 0;
        if (nextBtn) nextBtn.disabled = data.index === data.total - 1;

        // Load labels first
        const labelRes = await fetch(`/api/image_data/${data.image}?t=${Date.now()}`);
        appState.labels = await labelRes.json();
        appState.selectedLabelIndex = -1;

        // Set image source - this will trigger imgObj.onload which calls draw()
        imgObj.src = `/images/${data.image}?t=${Date.now()}`;

    } catch (e) {
        console.error(e);
        alert("Error loading image. Check console.");
    } finally {
        hideLoader();
    }
}

function prevImage() {
    if (appState.currentIndex > 0) {
        loadImage(appState.currentIndex - 1);
    }
}

function nextImage() {
    if (appState.currentIndex < appState.totalImages - 1) {
        loadImage(appState.currentIndex + 1);
    }
}

async function saveCurrent() {
    if (!appState.currentImage) return false;
    showLoader('Saving...');
    try {
        const payload = {
            username: USERNAME,
            filename: appState.currentImage,
            labels: appState.labels
        };
        const res = await fetch('/api/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        hideLoader();
        return data.status === 'success';
    } catch(e) {
        hideLoader();
        alert("Failed to save!");
        return false;
    }
}

async function saveAndNext() {
    const saved = await saveCurrent();
    if (saved) {
        if (appState.currentIndex < appState.totalImages - 1) {
            nextImage();
        } else {
            alert("Saved! This is the last image in your queue.");
            // Refetches the uncompleted state if applicable
            loadImage();
        }
    }
}

async function deleteCurrentImage() {
    if (!appState.currentImage) return;

    const confirmed = confirm(`Are you sure you want to permanently delete ${appState.currentImage}?\n\nThis will remove the image and its labels from the disk entirely. This action cannot be undone.`);
    if (!confirmed) return;

    showLoader('Deleting...');
    try {
        const res = await fetch('/api/delete_image', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username: USERNAME, filename: appState.currentImage })
        });
        const data = await res.json();

        if (data.status === 'success') {
            // Determine which index to load next
            // If we were at the end, load the new last image. Otherwise, load the same index (which is now the next image).
            const nextIndex = Math.min(appState.currentIndex, appState.totalImages - 2);

            if (nextIndex >= 0) {
                loadImage(nextIndex);
            } else {
                alert("No more images left.");
                window.location.href = '/';
            }
        } else {
            alert("Error deleting image: " + data.message);
            hideLoader();
        }
    } catch(e) {
        console.error(e);
        alert("Failed to delete.");
        hideLoader();
    }
}

async function renameUser() {
    const newName = prompt("Enter new name for this user:", USERNAME);
    if (newName && newName !== USERNAME) {
        showLoader('Renaming user...');
        try {
            const res = await fetch('/api/rename_user', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ old_name: USERNAME, new_name: newName })
            });
            const data = await res.json();
            if (data.status === 'success') {
                window.location.href = `/editor/${encodeURIComponent(data.new_name)}`;
            } else {
                alert("Error: " + data.message);
                hideLoader();
            }
        } catch (e) {
            console.error(e);
            alert("Failed to rename.");
            hideLoader();
        }
    }
}

async function addNewClass() {
    const input = document.getElementById('new-class-name');
    const name = input.value.trim();
    if (!name) return;

    const res = await fetch('/api/add_class', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name})
    });
    const data = await res.json();

    if (data.status === 'success') {
        appState.classes.push(name);
        renderClassList();
        appState.selectedClassId = data.id;
        updateClassSelection();
        input.value = '';
    } else {
        alert("Class already exists");
    }
}

// --- CANVAS LOGIC ---

function resizeCanvas() {
    const dim = getContainerSize();
    if (dim.w > 0 && dim.h > 0) {
        canvas.width = dim.w;
        canvas.height = dim.h;
    }
    draw();
}

function resetView() {
    if (!imgObj.src || !imgObj.width) return;

    const aspect = imgObj.width / imgObj.height;
    const canvasAspect = canvas.width / canvas.height;

    if (canvasAspect > aspect) {
        appState.scale = (canvas.height / imgObj.height) * 0.95;
    } else {
        appState.scale = (canvas.width / imgObj.width) * 0.95;
    }

    appState.panX = (canvas.width - (imgObj.width * appState.scale)) / 2;
    appState.panY = (canvas.height - (imgObj.height * appState.scale)) / 2;
    draw();
}

function applyZoom(factor) {
    appState.scale *= factor;
    draw();
}

function getHoverHandle(wx, wy) {
    if (appState.selectedLabelIndex === -1) return null;

    const l = appState.labels[appState.selectedLabelIndex];
    const x = (l.x - l.w/2) * imgObj.width;
    const y = (l.y - l.h/2) * imgObj.height;
    const w = l.w * imgObj.width;
    const h = l.h * imgObj.height;

    const hs = 10 / appState.scale; // Handle size

    if (dist(wx, wy, x, y) < hs) return 'tl';
    if (dist(wx, wy, x+w, y) < hs) return 'tr';
    if (dist(wx, wy, x, y+h) < hs) return 'bl';
    if (dist(wx, wy, x+w, y+h) < hs) return 'br';

    return null;
}

function dist(x1, y1, x2, y2) {
    return Math.sqrt((x1-x2)**2 + (y1-y2)**2);
}

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!imgObj.src || !imgObj.complete || imgObj.naturalWidth === 0) return;

    ctx.save();
    ctx.translate(appState.panX, appState.panY);
    ctx.scale(appState.scale, appState.scale);

    // Border around image
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1 / appState.scale;
    ctx.strokeRect(0, 0, imgObj.width, imgObj.height);

    // Image
    ctx.drawImage(imgObj, 0, 0);

    // Labels
    const handleSize = 6 / appState.scale;

    appState.labels.forEach((l, index) => {
        const isSelected = (index === appState.selectedLabelIndex);

        const x = (l.x - l.w / 2) * imgObj.width;
        const y = (l.y - l.h / 2) * imgObj.height;
        const w = l.w * imgObj.width;
        const h = l.h * imgObj.height;

        const color = COLORS[l.class_id % COLORS.length];

        ctx.strokeStyle = color;
        ctx.lineWidth = isSelected ? (3 / appState.scale) : (2 / appState.scale);

        if (isSelected) {
            ctx.fillStyle = color + '33';
            ctx.fillRect(x, y, w, h);
        }
        ctx.strokeRect(x, y, w, h);

        // Handles
        if (isSelected) {
            ctx.fillStyle = '#fff';
            ctx.fillRect(x - handleSize/2, y - handleSize/2, handleSize, handleSize);
            ctx.fillRect(x + w - handleSize/2, y - handleSize/2, handleSize, handleSize);
            ctx.fillRect(x - handleSize/2, y + h - handleSize/2, handleSize, handleSize);
            ctx.fillRect(x + w - handleSize/2, y + h - handleSize/2, handleSize, handleSize);
        }

        // Text (class name + species if available)
        ctx.save();
        ctx.fillStyle = color;
        ctx.font = `${14 / appState.scale}px Arial`;
        const className = appState.classes[l.class_id] || `Class ${l.class_id}`;
        const speciesText = l.species ? ` - ${l.species}` : '';
        const text = className + speciesText;
        const textWidth = ctx.measureText(text).width;

        // Draw background for text
        ctx.fillStyle = color;
        ctx.fillRect(x, y - (20/appState.scale), textWidth + (8/appState.scale), (20/appState.scale));

        // Draw text
        ctx.fillStyle = 'black';
        ctx.fillText(text, x + (4/appState.scale), y - (5/appState.scale));
        ctx.restore();
    });

    // Draw AI detection points
    if (appState.samPoints.length > 0) {
        const time = Date.now();
        appState.samPoints.forEach((pt, index) => {
            const radius = 8 / appState.scale;

            // Apply glowing effect for processing points
            if (pt.processing) {
                const glowIntensity = (Math.sin(time / 200) + 1) / 2; // 0 to 1
                const glowRadius = radius + (glowIntensity * 3 / appState.scale);

                // Outer glow
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, glowRadius, 0, 2 * Math.PI);
                ctx.fillStyle = `rgba(255, 255, 0, ${0.3 + glowIntensity * 0.3})`;
                ctx.fill();
            }

            // Draw outer circle
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, radius, 0, 2 * Math.PI);
            ctx.fillStyle = pt.processing ? '#FFFF00' : '#00FF00'; // Yellow when processing, green otherwise
            ctx.fill();
            ctx.strokeStyle = '#FFFFFF';
            ctx.lineWidth = 2 / appState.scale;
            ctx.stroke();

            // Draw number
            ctx.fillStyle = '#000000';
            ctx.font = `bold ${12 / appState.scale}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText((index + 1).toString(), pt.x, pt.y);
        });
        ctx.textAlign = 'left';
        ctx.textBaseline = 'alphabetic';

        // Keep redrawing while any points are processing
        if (appState.samPoints.some(pt => pt.processing)) {
            if (!appState.samAnimationFrame) {
                appState.samAnimationFrame = requestAnimationFrame(() => {
                    appState.samAnimationFrame = null;
                    draw();
                });
            }
        }
    }

    ctx.restore();

    // Update Selected Box Actions Visibility
    const actionsDiv = document.getElementById('selected-box-actions');

    if (appState.selectedLabelIndex !== -1) {
        actionsDiv.style.display = 'block';
        // Update species dropdown to show current species
        const currentLabel = appState.labels[appState.selectedLabelIndex];
        const speciesSelect = document.getElementById('species-select');
        if (speciesSelect && currentLabel) {
            speciesSelect.value = currentLabel.species || '';
        }
    } else {
        actionsDiv.style.display = 'none';
    }
}

// --- MODE SELECTION ---
// --- AI DETECTION INTERACTION ---

async function processSinglePoint(pointIndex) {
    // Process a single detection point non-blocking (with selected mode)
    if (!appState.currentImage || pointIndex >= appState.samPoints.length) return;

    const pt = appState.samPoints[pointIndex];
    if (pt.processing) return; // Already processing

    // Mark as processing
    pt.processing = true;
    draw();

    // Log for user feedback
    console.log(`🤖 Detecting bird at point ${pointIndex + 1}...`);

    // Convert world coordinates to normalized
    const normalizedPoint = {
        x: clamp(pt.x / imgObj.width, 0, 1),
        y: clamp(pt.y / imgObj.height, 0, 1)
    };

    try {
        const res = await fetch('/api/sam_segment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                filename: appState.currentImage,
                point: normalizedPoint,
                point_index: pointIndex,
                mode: 'fast'
            })
        });

        const data = await res.json();

        if (data.status === 'success' && data.box) {
            // Add the box to labels
            appState.labels.push({
                class_id: appState.selectedClassId,
                x: data.box.x,
                y: data.box.y,
                w: data.box.w,
                h: data.box.h
            });

            // Remove the processed point
            appState.samPoints = appState.samPoints.filter((_, i) => i !== pointIndex);

            console.log(`✅ Bird detected at point ${pointIndex + 1} (conf: ${data.confidence?.toFixed(2) || 'N/A'}, dist: ${data.distance?.toFixed(0) || 'N/A'}px)`);

            draw();
        } else {
            console.error('❌ Detection failed for point', pointIndex, ':', data.message);
            // Mark as not processing so user can retry
            pt.processing = false;
            draw();
        }
    } catch (e) {
        console.error('Detection error for point', pointIndex, ':', e);
        // Mark as not processing so user can retry
        if (appState.samPoints[pointIndex]) {
            appState.samPoints[pointIndex].processing = false;
        }
        draw();
    }
}

async function runSAM() {
    // Legacy function for Enter key - process all pending detection points
    if (!appState.currentImage || appState.samPoints.length === 0) return;

    // Get all non-processing points
    const pendingPoints = appState.samPoints
        .map((pt, index) => ({ pt, index }))
        .filter(({ pt }) => !pt.processing);

    if (pendingPoints.length === 0) return;

    console.log(`🤖 Batch detecting ${pendingPoints.length} birds...`);

    // Trigger processing for all pending points
    pendingPoints.forEach(({ index }) => {
        processSinglePoint(index);
    });
}

async function runAutoDetect() {
    if (!appState.currentImage || appState.samProcessing) return;

    const confirmed = confirm(
        'Auto-detect will find ALL birds in this image using the USGS AI model.\n\n' +
        'This typically takes 2-5 seconds.\n\n' +
        'Continue?'
    );

    if (!confirmed) return;

    appState.samProcessing = true;
    showLoader('Running USGS bird detection... Finding all birds!');

    try {
        const res = await fetch('/api/sam_auto_detect', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                filename: appState.currentImage,
                min_size: 10,  // Adjust these based on your birds
                max_size: 400
            })
        });

        const data = await res.json();

        if (data.status === 'success' && data.boxes) {
            // Add all detected boxes to labels
            let addedCount = 0;
            data.boxes.forEach(box => {
                appState.labels.push({
                    class_id: appState.selectedClassId,
                    x: box.x,
                    y: box.y,
                    w: box.w,
                    h: box.h
                });
                addedCount++;
            });

            draw();
            alert(`🤖 USGS model detected ${addedCount} birds!\n\nReview them and delete any false positives using Edit mode (E).`);
        } else {
            alert('Auto-detect failed: ' + (data.message || 'Unknown error'));
        }
    } catch (e) {
        console.error('Auto-detect error:', e);
        alert('Auto-detect failed. Check console.');
    } finally {
        appState.samProcessing = false;
        hideLoader();
    }
}

// --- INTERACTION ---

function onMouseDown(e) {
    const m = getMousePos(e);
    const w = toWorld(m.x, m.y);

    // 1. Pan (Space held OR Pan tool OR Middle/Right click)
    if (appState.isSpaceHeld || appState.tool === 'pan' || e.button === 1 || e.button === 2) {
        appState.mode = 'DRAGGING_VIEW';
        appState.startX = m.x;
        appState.startY = m.y;
        updateCursor();
        return;
    }

    // 2. AI Detect Mode - Directly process the click
    if (appState.tool === 'sam' && e.button === 0) {
        const clampedX = clamp(w.x, 0, imgObj.width);
        const clampedY = clamp(w.y, 0, imgObj.height);

        // Process immediately with fast mode
        const pointIndex = appState.samPoints.length;
        appState.samPoints.push({
            x: clampedX,
            y: clampedY,
            processing: false,
            pointIndex: pointIndex
        });
        draw();

        // Immediately trigger detection for this point (non-blocking)
        processSinglePoint(pointIndex);
        return;
    }

    // 3. Edit Mode Interaction
    if (appState.tool === 'edit') {
        // Check Handles
        const handle = getHoverHandle(w.x, w.y);
        if (handle) {
            appState.mode = 'RESIZING';
            appState.resizeHandle = handle;
            appState.startX = clamp(w.x, 0, imgObj.width);
            appState.startY = clamp(w.y, 0, imgObj.height);
            return;
        }

        // Check Selection
        let found = -1;
        let minArea = Infinity;

        appState.labels.forEach((l, i) => {
            const lx = (l.x - l.w/2) * imgObj.width;
            const ly = (l.y - l.h/2) * imgObj.height;
            const lw = l.w * imgObj.width;
            const lh = l.h * imgObj.height;

            if (w.x >= lx && w.x <= lx+lw && w.y >= ly && w.y <= ly+lh) {
                const area = lw * lh;
                if (area < minArea) {
                    minArea = area;
                    found = i;
                }
            }
        });

        if (found !== -1) {
            appState.selectedLabelIndex = found;
            appState.mode = 'MOVING';
            appState.startX = w.x;
            appState.startY = w.y;
            draw();
            return;
        } else {
            appState.selectedLabelIndex = -1;
            draw();
        }
    }

    // 4. Draw Mode
    if (appState.tool === 'draw' && e.button === 0) {
        appState.selectedLabelIndex = -1;
        appState.mode = 'DRAWING';
        appState.startX = clamp(w.x, 0, imgObj.width);
        appState.startY = clamp(w.y, 0, imgObj.height);
        draw();
    }
}

function onMouseMove(e) {
    const m = getMousePos(e);
    const w = toWorld(m.x, m.y);

    // Update Cursor dynamically in edit mode
    if (appState.tool === 'edit' && appState.mode === 'IDLE') {
         const handle = getHoverHandle(w.x, w.y);
         if (handle) canvas.style.cursor = 'move';
         else canvas.style.cursor = 'default';
    }

    if (appState.mode === 'IDLE') return;

    // View Drag
    if (appState.mode === 'DRAGGING_VIEW') {
        appState.panX += (m.x - appState.startX);
        appState.panY += (m.y - appState.startY);
        appState.startX = m.x;
        appState.startY = m.y;
        draw();
        return;
    }

    const clampedX = clamp(w.x, 0, imgObj.width);
    const clampedY = clamp(w.y, 0, imgObj.height);

    // Drawing
    if (appState.mode === 'DRAWING') {
        draw();
        ctx.save();
        ctx.translate(appState.panX, appState.panY);
        ctx.scale(appState.scale, appState.scale);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2 / appState.scale;
        ctx.setLineDash([5/appState.scale, 5/appState.scale]);
        ctx.strokeRect(appState.startX, appState.startY, clampedX - appState.startX, clampedY - appState.startY);
        ctx.restore();
        return;
    }

    // Resizing
    if (appState.mode === 'RESIZING') {
        const l = appState.labels[appState.selectedLabelIndex];
        let lx = (l.x - l.w/2) * imgObj.width;
        let ly = (l.y - l.h/2) * imgObj.height;
        let rx = lx + l.w * imgObj.width;
        let ry = ly + l.h * imgObj.height;

        if (appState.resizeHandle.includes('l')) lx = clampedX;
        if (appState.resizeHandle.includes('r')) rx = clampedX;
        if (appState.resizeHandle.includes('t')) ly = clampedY;
        if (appState.resizeHandle.includes('b')) ry = clampedY;

        const newW = Math.abs(rx - lx);
        const newH = Math.abs(ry - ly);
        const newX = Math.min(lx, rx) + newW/2;
        const newY = Math.min(ly, ry) + newH/2;

        l.x = newX / imgObj.width;
        l.y = newY / imgObj.height;
        l.w = newW / imgObj.width;
        l.h = newH / imgObj.height;
        draw();
    }

    // Moving
    if (appState.mode === 'MOVING') {
        const dx = clampedX - appState.startX;
        const dy = clampedY - appState.startY;

        const l = appState.labels[appState.selectedLabelIndex];
        l.x += dx / imgObj.width;
        l.y += dy / imgObj.height;

        appState.startX = clampedX;
        appState.startY = clampedY;
        draw();
    }
}

function onMouseUp(e) {
    if (appState.mode === 'DRAWING') {
        const m = getMousePos(e);
        let w = toWorld(m.x, m.y);
        const endX = clamp(w.x, 0, imgObj.width);
        const endY = clamp(w.y, 0, imgObj.height);

        let width = Math.abs(endX - appState.startX);
        let height = Math.abs(endY - appState.startY);

        if (width > 5 && height > 5) {
            const cx = (Math.min(appState.startX, endX) + width/2) / imgObj.width;
            const cy = (Math.min(appState.startY, endY) + height/2) / imgObj.height;

            appState.labels.push({
                class_id: appState.selectedClassId,
                x: cx, y: cy, w: width/imgObj.width, h: height/imgObj.height
            });
        }
    }

    appState.mode = 'IDLE';
    appState.resizeHandle = null;
    updateCursor();
    draw();
}

function onWheel(e) {
    e.preventDefault();

    // Ctrl + Wheel = ZOOM
    if (e.ctrlKey) {
        const zoomIntensity = 0.1;
        const wheel = e.deltaY < 0 ? 1 : -1;
        const zoom = Math.exp(wheel * zoomIntensity);

        const m = getMousePos(e);
        const w = toWorld(m.x, m.y);

        appState.scale *= zoom;
        appState.panX = m.x - w.x * appState.scale;
        appState.panY = m.y - w.y * appState.scale;
    }
    // Regular Wheel = PAN/SCROLL
    else {
        // Scroll factors
        const scrollSpeed = 0.8;
        appState.panX -= e.deltaX * scrollSpeed;
        appState.panY -= e.deltaY * scrollSpeed;
    }
    draw();
}

function handleKeyDown(e) {
    // Spacebar logic for Hand tool
    if (e.code === 'Space' && !e.repeat) {
        // If Shift is also held, do save
        if (e.shiftKey) {
            e.preventDefault();
            saveAndNext();
            return;
        }
        // Otherwise enable temp hand
        if (document.activeElement.tagName !== 'INPUT') { // Don't trigger if typing class name
            appState.isSpaceHeld = true;
            updateCursor();
            e.preventDefault();
        }
    }

    // Tool Shortcuts
    if (document.activeElement.tagName !== 'INPUT') {
        if (e.key.toLowerCase() === 'd') setTool('draw');
        if (e.key.toLowerCase() === 's') setTool('sam');
        if (e.key.toLowerCase() === 'e') setTool('edit');
        if (e.key.toLowerCase() === 'h') setTool('pan');
        if (e.key.toLowerCase() === 'r') resetView();
        if (e.key === 'Backspace' || e.key === 'Delete') deleteSelected();

        // AI Detect Mode Controls
        if (e.key === 'Enter' && appState.tool === 'sam' && appState.samPoints.length > 0) {
            e.preventDefault();
            runSAM(); // Batch process all pending detection points
        }
        if (e.key === 'Escape' && appState.samPoints.length > 0) {
            e.preventDefault();
            appState.samPoints = [];
            draw();
        }
    }
}

function handleKeyUp(e) {
    if (e.code === 'Space') {
        appState.isSpaceHeld = false;
        appState.mode = 'IDLE'; // Release drag if active
        updateCursor();
    }
}

function deleteSelected() {
    if (appState.selectedLabelIndex !== -1) {
        appState.labels.splice(appState.selectedLabelIndex, 1);
        appState.selectedLabelIndex = -1;
        draw();
    }
}

// --- UI HELPERS ---

function renderClassList() {
    const list = document.getElementById('class-list');
    list.innerHTML = '';

    appState.classes.forEach((c, i) => {
        const div = document.createElement('div');
        div.className = `class-item ${i === appState.selectedClassId ? 'active' : ''}`;
        div.onclick = () => {
            appState.selectedClassId = i;
            updateClassSelection();
        };

        const colorSpan = document.createElement('span');
        colorSpan.className = 'class-color';
        colorSpan.style.backgroundColor = COLORS[i % COLORS.length];

        const nameSpan = document.createElement('span');
        nameSpan.className = 'class-name';
        nameSpan.innerText = c;

        div.appendChild(colorSpan);
        div.appendChild(nameSpan);
        list.appendChild(div);
    });
}

function updateClassSelection() {
    const items = document.querySelectorAll('.class-item');
    items.forEach((item, i) => {
        if (i === appState.selectedClassId) item.classList.add('active');
        else item.classList.remove('active');
    });
}

function renderSpeciesList() {
    const speciesSelect = document.getElementById('species-select');
    if (!speciesSelect) return;

    // Clear existing options (keep first placeholder)
    speciesSelect.innerHTML = '<option value="">Select Species...</option>';

    // Add species options
    appState.speciesList.forEach(species => {
        const option = document.createElement('option');
        option.value = species.code;
        option.textContent = `${species.code} - ${species.name}`;
        speciesSelect.appendChild(option);
    });

    // Add event listener for species selection
    speciesSelect.onchange = function() {
        if (appState.selectedLabelIndex !== -1) {
            const selectedSpecies = this.value;
            appState.labels[appState.selectedLabelIndex].species = selectedSpecies;
            draw(); // Redraw to show species in label
        }
    };
}

function showLoader(msg) {
    document.getElementById('loader').style.display = 'flex';
    document.getElementById('loader-text').innerText = msg;
}

function hideLoader() {
    document.getElementById('loader').style.display = 'none';
}

// Check service status
async function checkServiceStatus() {
    try {
        const response = await fetch('http://localhost:8000/services/status');
        const data = await response.json();

        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');

        const services = data.services || {};
        const runningCount = Object.values(services).filter(s => s.status === 'running').length;
        const totalCount = Object.keys(services).length;

        if (data.overall_status === 'healthy') {
            statusIndicator.className = 'status-dot status-running';
            statusText.textContent = 'All Services Online';
        } else if (runningCount > 0) {
            statusIndicator.className = 'status-dot status-offline';
            statusText.textContent = `${runningCount}/${totalCount} Services Online`;
        } else {
            statusIndicator.className = 'status-dot status-offline';
            statusText.textContent = 'Services Offline';
        }
    } catch (error) {
        document.getElementById('status-indicator').className = 'status-dot status-offline';
        document.getElementById('status-text').textContent = 'Status Unavailable';
    }
}

// --- AUTO-INITIALIZATION ---
// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        init();
        checkServiceStatus();
        setInterval(checkServiceStatus, 30000);
    });
} else {
    // DOM is already ready
    init();
    checkServiceStatus();
    setInterval(checkServiceStatus, 30000);
}
