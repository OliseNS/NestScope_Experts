/**
 * Nestperts Classify Tab Module
 *
 * This module handles the species classification interface where users can:
 * - View all bounding boxes as a list with thumbnails
 * - Assign species to individual boxes
 * - Highlight boxes on the canvas by clicking them
 * - Apply species to all boxes at once (bulk operation)
 */

/**
 * Render the bounding box list in the Classify tab.
 *
 * This function generates a visual list of all detected bounding boxes,
 * each with a thumbnail, class label, and species dropdown. Users can
 * click on a box to highlight it on the canvas.
 */
function renderBBoxList() {
    const bboxList = document.getElementById('bbox-list');
    const bboxCount = document.getElementById('bbox-count');

    if (!bboxList || !bboxCount) return;

    // Update count
    bboxCount.textContent = appState.labels.length;

    // Clear existing list
    bboxList.innerHTML = '';

    // Handle empty state
    if (appState.labels.length === 0) {
        bboxList.innerHTML = `
            <div style="text-align: center; padding: 40px 20px; color: #888;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📦</div>
                <p style="margin: 0; font-size: 1.1rem;">No bounding boxes yet</p>
                <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #666;">
                    Switch to <strong>Draw Boxes</strong> tab to add some!
                </p>
            </div>
        `;
        return;
    }

    // Create header with bulk operations
    const header = createBulkOperationsHeader();
    bboxList.appendChild(header);

    // Create list items for each bounding box
    appState.labels.forEach((label, index) => {
        const item = createBBoxListItem(label, index);
        bboxList.appendChild(item);
    });
}

/**
 * Create the bulk operations header.
 *
 * This header allows users to apply a species to all boxes at once,
 * which is useful when all birds in an image are the same species.
 */
function createBulkOperationsHeader() {
    const header = document.createElement('div');
    header.className = 'bbox-bulk-operations';
    header.style.cssText = `
        background: #252525;
        padding: 12px 16px;
        margin-bottom: 12px;
        border-radius: 6px;
        border: 1px solid #333;
        display: flex;
        align-items: center;
        gap: 12px;
    `;

    header.innerHTML = `
        <span style="color: #999; font-size: 0.85rem; flex-shrink: 0;">Apply to all:</span>
        <select id="bulk-species-select" style="
            flex: 1;
            padding: 6px 10px;
            background: #1E1E1E;
            color: #E0E0E0;
            border: 1px solid #444;
            border-radius: 4px;
            font-size: 0.875rem;
            cursor: pointer;
        ">
            <option value="">Select species...</option>
        </select>
        <button id="bulk-apply-btn" style="
            padding: 6px 16px;
            background: #CC785C;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 0.875rem;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s;
        ">Apply</button>
    `;

    // Populate species dropdown
    const bulkSelect = header.querySelector('#bulk-species-select');
    appState.speciesList.forEach(species => {
        const option = document.createElement('option');
        option.value = species.code;
        option.textContent = `${species.code} - ${species.name}`;
        bulkSelect.appendChild(option);
    });

    // Add event listener for bulk apply
    const applyBtn = header.querySelector('#bulk-apply-btn');
    applyBtn.addEventListener('click', () => {
        const selectedSpecies = bulkSelect.value;
        if (!selectedSpecies) {
            alert('Please select a species first');
            return;
        }
        applySpeciesToAll(selectedSpecies);
    });

    // Hover effect for button
    applyBtn.addEventListener('mouseenter', () => {
        applyBtn.style.background = '#B86A4C';
    });
    applyBtn.addEventListener('mouseleave', () => {
        applyBtn.style.background = '#CC785C';
    });

    return header;
}

/**
 * Create a list item for a single bounding box.
 *
 * Each item shows:
 * - Thumbnail of the cropped region
 * - Class name with color indicator
 * - Species dropdown
 * - Box dimensions
 *
 * @param {Object} label - The label object {class_id, x, y, w, h, species}
 * @param {number} index - Index in the labels array
 */
function createBBoxListItem(label, index) {
    const item = document.createElement('div');
    item.className = 'bbox-list-item';
    item.dataset.index = index;

    const isSelected = (index === appState.selectedLabelIndex);
    const color = COLORS[label.class_id % COLORS.length];
    const className = appState.classes[label.class_id] || `Class ${label.class_id}`;

    // Calculate pixel dimensions for display
    const pixelWidth = Math.round(label.w * (imgObj.width || 0));
    const pixelHeight = Math.round(label.h * (imgObj.height || 0));

    item.style.cssText = `
        background: ${isSelected ? '#2A2A2A' : '#1E1E1E'};
        border: 2px solid ${isSelected ? color : '#333'};
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        gap: 12px;
        align-items: center;
    `;

    // Thumbnail container
    const thumbnailContainer = document.createElement('div');
    thumbnailContainer.style.cssText = `
        width: 80px;
        height: 80px;
        background: #0F0F0F;
        border-radius: 6px;
        border: 2px solid ${color};
        overflow: hidden;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    `;

    // Generate thumbnail
    const thumbnail = generateThumbnail(label);
    thumbnailContainer.appendChild(thumbnail);

    // Info container
    const infoContainer = document.createElement('div');
    infoContainer.style.cssText = `
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-width: 0;
    `;

    // Box info (class and dimensions)
    const boxInfo = document.createElement('div');
    boxInfo.style.cssText = `
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.875rem;
    `;
    boxInfo.innerHTML = `
        <span style="
            display: inline-block;
            width: 12px;
            height: 12px;
            background: ${color};
            border-radius: 2px;
        "></span>
        <span style="color: #E0E0E0; font-weight: 500;">${className}</span>
        <span style="color: #666; font-size: 0.75rem;">${pixelWidth}×${pixelHeight}px</span>
    `;

    // Species dropdown
    const speciesContainer = document.createElement('div');
    speciesContainer.style.cssText = `
        display: flex;
        align-items: center;
        gap: 8px;
    `;

    const speciesSelect = document.createElement('select');
    speciesSelect.className = 'bbox-species-select';
    speciesSelect.dataset.index = index;
    speciesSelect.style.cssText = `
        flex: 1;
        padding: 4px 8px;
        background: #252525;
        color: #E0E0E0;
        border: 1px solid #444;
        border-radius: 4px;
        font-size: 0.813rem;
        cursor: pointer;
    `;

    // Populate species options
    speciesSelect.innerHTML = '<option value="">Select species...</option>';
    appState.speciesList.forEach(species => {
        const option = document.createElement('option');
        option.value = species.code;
        option.textContent = `${species.code} - ${species.name}`;
        if (label.species === species.code) {
            option.selected = true;
        }
        speciesSelect.appendChild(option);
    });

    // Species select event (stop propagation to prevent box selection)
    speciesSelect.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    speciesSelect.addEventListener('change', (e) => {
        e.stopPropagation();
        const newSpecies = e.target.value;
        assignSpeciesToBox(index, newSpecies);
    });

    // Status indicator
    const statusIndicator = document.createElement('span');
    statusIndicator.style.cssText = `
        font-size: 1.2rem;
        flex-shrink: 0;
    `;
    statusIndicator.textContent = label.species ? '✅' : '⚠️';
    statusIndicator.title = label.species ? 'Species assigned' : 'No species assigned';

    speciesContainer.appendChild(speciesSelect);
    speciesContainer.appendChild(statusIndicator);

    // Assemble the item
    infoContainer.appendChild(boxInfo);
    infoContainer.appendChild(speciesContainer);
    item.appendChild(thumbnailContainer);
    item.appendChild(infoContainer);

    // Click handler - highlight box on canvas
    item.addEventListener('click', () => {
        selectBoxFromList(index);
    });

    // Hover effect
    item.addEventListener('mouseenter', () => {
        if (index !== appState.selectedLabelIndex) {
            item.style.background = '#252525';
            item.style.borderColor = '#444';
        }
    });

    item.addEventListener('mouseleave', () => {
        if (index !== appState.selectedLabelIndex) {
            item.style.background = '#1E1E1E';
            item.style.borderColor = '#333';
        }
    });

    return item;
}

/**
 * Generate a thumbnail canvas for a bounding box.
 *
 * This creates a small preview of the cropped region of the image
 * corresponding to the bounding box.
 *
 * @param {Object} label - The label object {x, y, w, h, ...}
 * @returns {HTMLCanvasElement} A canvas element with the thumbnail
 */
function generateThumbnail(label) {
    const canvas = document.createElement('canvas');
    canvas.width = 80;
    canvas.height = 80;
    const ctx = canvas.getContext('2d');

    // If image isn't loaded yet, show placeholder
    if (!imgObj.complete || !imgObj.naturalWidth) {
        ctx.fillStyle = '#0F0F0F';
        ctx.fillRect(0, 0, 80, 80);
        ctx.fillStyle = '#666';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Loading...', 40, 40);
        return canvas;
    }

    // Calculate source region (in image coordinates)
    const sx = (label.x - label.w / 2) * imgObj.width;
    const sy = (label.y - label.h / 2) * imgObj.height;
    const sw = label.w * imgObj.width;
    const sh = label.h * imgObj.height;

    // Calculate aspect ratio and fit to 80x80
    const aspectRatio = sw / sh;
    let dw, dh, dx, dy;

    if (aspectRatio > 1) {
        // Wider than tall
        dw = 80;
        dh = 80 / aspectRatio;
        dx = 0;
        dy = (80 - dh) / 2;
    } else {
        // Taller than wide
        dh = 80;
        dw = 80 * aspectRatio;
        dy = 0;
        dx = (80 - dw) / 2;
    }

    // Fill background
    ctx.fillStyle = '#0F0F0F';
    ctx.fillRect(0, 0, 80, 80);

    // Draw cropped region
    try {
        ctx.drawImage(imgObj, sx, sy, sw, sh, dx, dy, dw, dh);
    } catch (e) {
        console.error('Failed to draw thumbnail:', e);
        ctx.fillStyle = '#666';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Error', 40, 40);
    }

    return canvas;
}

/**
 * Select a box from the list and highlight it on the canvas.
 *
 * This function:
 * - Updates the selected index in appState
 * - Switches to edit tool (so user can adjust the box if needed)
 * - Redraws the canvas to show the selection
 * - Re-renders the list to update highlighting
 *
 * @param {number} index - Index of the box to select
 */
function selectBoxFromList(index) {
    // Update selection
    appState.selectedLabelIndex = index;

    // Switch to edit tool to allow box adjustment
    setTool('edit');

    // Redraw canvas to show selection
    draw();

    // Re-render the list to update highlighting
    renderBBoxList();

    console.log(`Selected box ${index + 1}/${appState.labels.length}`);
}

/**
 * Assign a species to a specific bounding box.
 *
 * @param {number} index - Index of the box
 * @param {string} speciesCode - Species code (e.g., "BRPE", "ROTE")
 */
async function assignSpeciesToBox(index, speciesCode) {
    if (index < 0 || index >= appState.labels.length) {
        console.error('Invalid box index:', index);
        return;
    }

    // Update the label
    appState.labels[index].species = speciesCode || undefined;

    // Redraw canvas to show updated species label
    draw();

    // Re-render the list to update checkmark
    renderBBoxList();

    // Auto-save to persist the change
    await autoSaveLabels();

    // Show feedback
    const speciesName = appState.speciesList.find(s => s.code === speciesCode)?.name || 'None';
    console.log(`Box ${index + 1}: Species set to ${speciesCode} (${speciesName})`);
}

/**
 * Apply a species to all bounding boxes (bulk operation).
 *
 * This is useful when all birds in an image are the same species,
 * allowing the user to classify them all at once.
 *
 * @param {string} speciesCode - Species code to apply to all boxes
 */
async function applySpeciesToAll(speciesCode) {
    if (!speciesCode) return;

    // Apply to all labels
    appState.labels.forEach(label => {
        label.species = speciesCode;
    });

    // Redraw and re-render
    draw();
    renderBBoxList();

    // Auto-save to persist the changes
    await autoSaveLabels();

    // Show feedback
    const speciesName = appState.speciesList.find(s => s.code === speciesCode)?.name || speciesCode;
    console.log(`✅ Applied ${speciesCode} (${speciesName}) to all ${appState.labels.length} boxes`);

    // Show toast notification
    showToast(`Applied ${speciesCode} to ${appState.labels.length} boxes`, 'success');
}

/**
 * Auto-save labels to the backend after species assignment.
 *
 * This function is called automatically after any species assignment
 * (individual or bulk) to persist changes to disk immediately.
 * This ensures species assignments are not lost on page reload.
 */
async function autoSaveLabels() {
    if (!appState.currentImage) {
        console.warn('No current image to save');
        return;
    }

    // Show subtle saving indicator
    showSavingIndicator(true);

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

        if (data.status === 'success') {
            console.log('💾 Auto-saved species assignments');
            showSavingIndicator(false, true); // Show checkmark briefly
        } else {
            console.error('❌ Auto-save failed:', data);
            showSavingIndicator(false);
            showToast('Failed to save species assignments', 'error');
        }
    } catch (e) {
        console.error('❌ Auto-save error:', e);
        showSavingIndicator(false);
        showToast('Error saving species assignments', 'error');
    }
}

/**
 * Show/hide a subtle saving indicator in the UI.
 *
 * @param {boolean} saving - True to show "Saving...", false to hide
 * @param {boolean} success - If true, briefly show success checkmark
 */
function showSavingIndicator(saving, success = false) {
    let indicator = document.getElementById('saving-indicator');

    if (!indicator) {
        // Create indicator if it doesn't exist
        indicator = document.createElement('div');
        indicator.id = 'saving-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 70px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 0.875rem;
            display: none;
            align-items: center;
            gap: 8px;
            z-index: 9999;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        `;
        document.body.appendChild(indicator);
    }

    if (saving) {
        indicator.innerHTML = `
            <span style="animation: spin 1s linear infinite; display: inline-block;">⟳</span>
            <span>Saving...</span>
        `;
        indicator.style.display = 'flex';

        // Add spin animation if not exists
        if (!document.getElementById('spin-animation')) {
            const style = document.createElement('style');
            style.id = 'spin-animation';
            style.textContent = `
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }
    } else if (success) {
        indicator.innerHTML = `
            <span>✓</span>
            <span>Saved</span>
        `;
        indicator.style.display = 'flex';
        indicator.style.background = 'rgba(76, 175, 80, 0.9)';

        // Hide after 1.5 seconds
        setTimeout(() => {
            indicator.style.display = 'none';
            indicator.style.background = 'rgba(0, 0, 0, 0.8)';
        }, 1500);
    } else {
        indicator.style.display = 'none';
    }
}

/**
 * Show a temporary toast notification.
 *
 * This provides visual feedback for bulk operations.
 *
 * @param {string} message - Message to display
 * @param {string} type - Type of message ('success', 'error', 'info')
 */
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#FF6464' : '#2196F3'};
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        font-size: 0.9rem;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    toast.textContent = message;

    // Add animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }
    `;
    document.head.appendChild(style);

    document.body.appendChild(toast);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Export functions for use by editor-core.js
// (In a module system, these would be proper exports. Here they're global.)
window.renderBBoxList = renderBBoxList;
window.selectBoxFromList = selectBoxFromList;
window.assignSpeciesToBox = assignSpeciesToBox;
window.applySpeciesToAll = applySpeciesToAll;
window.autoSaveLabels = autoSaveLabels;
