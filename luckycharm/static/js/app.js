// LuckyCharm - Bird Detection Speed Demo App

let isProcessing = false;
let statusInterval = null;
let currentResults = [];

// DOM Elements
const gong = document.getElementById('gong');
const gongContainer = document.getElementById('gongContainer');
const ripple = document.getElementById('ripple');
const gongInstruction = document.getElementById('gongInstruction');
const statsSection = document.getElementById('statsSection');
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');
const summarySection = document.getElementById('summarySection');
const gallery = document.getElementById('gallery');

// Stats elements
const imagesProcessed = document.getElementById('imagesProcessed');
const birdsDetected = document.getElementById('birdsDetected');
const processingSpeed = document.getElementById('processingSpeed');
const elapsedTime = document.getElementById('elapsedTime');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');

// Gong click handler
gongContainer.addEventListener('click', () => {
    if (!isProcessing) {
        startProcessing();
    } else {
        stopProcessing();
    }
});

// Start processing
async function startProcessing() {
    try {
        // Play gong sound
        if (window.playGongSound) {
            window.playGongSound();
        }

        // Animate gong
        gong.classList.add('hit');
        ripple.classList.add('active');

        setTimeout(() => {
            gong.classList.remove('hit');
            ripple.classList.remove('active');
        }, 600);

        // Call API to start processing
        const response = await fetch('/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            throw new Error('Failed to start processing');
        }

        // Update UI
        isProcessing = true;
        gong.classList.add('processing');
        gongInstruction.textContent = 'Click the gong again to stop!';
        statsSection.style.display = 'grid';
        progressSection.style.display = 'block';
        resultsSection.style.display = 'block';

        // Clear previous results
        gallery.innerHTML = '';
        currentResults = [];

        // Start polling for status
        statusInterval = setInterval(updateStatus, 500);

    } catch (error) {
        console.error('Error starting processing:', error);
        alert('Failed to start processing. Please try again.');
    }
}

// Stop processing
async function stopProcessing() {
    try {
        // Play gong sound
        if (window.playGongSound) {
            window.playGongSound();
        }

        // Animate gong
        gong.classList.add('hit');
        ripple.classList.add('active');

        setTimeout(() => {
            gong.classList.remove('hit');
            ripple.classList.remove('active');
        }, 600);

        // Call API to stop processing
        const response = await fetch('/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            throw new Error('Failed to stop processing');
        }

        // Update UI
        isProcessing = false;
        gong.classList.remove('processing');
        gongInstruction.textContent = 'Processing stopped!';

        // Stop polling
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }

        // Show summary
        showSummary();

    } catch (error) {
        console.error('Error stopping processing:', error);
        alert('Failed to stop processing.');
    }
}

// Update status from server
async function updateStatus() {
    try {
        const response = await fetch('/status');
        const data = await response.json();

        // Update stats
        imagesProcessed.textContent = data.current_image;
        birdsDetected.textContent = data.total_birds;
        processingSpeed.textContent = data.images_per_second.toFixed(2);
        elapsedTime.textContent = formatTime(data.elapsed_time);

        // Update progress bar
        if (data.total_images > 0) {
            const progress = (data.current_image / data.total_images) * 100;
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `${data.current_image} / ${data.total_images} images`;
        }

        // Check if processing completed
        if (!data.active && data.current_image > 0) {
            isProcessing = false;
            gong.classList.remove('processing');
            gongInstruction.textContent = 'Processing complete!';

            if (statusInterval) {
                clearInterval(statusInterval);
                statusInterval = null;
            }

            // Load final results
            await loadResults();
            showSummary();
        } else if (data.active) {
            // Load new results incrementally
            await loadResults();
        }

    } catch (error) {
        console.error('Error updating status:', error);
    }
}

// Load processed images
async function loadResults() {
    try {
        const response = await fetch('/results');
        const data = await response.json();

        // Add new images to gallery
        const newImages = data.images.slice(currentResults.length);

        newImages.forEach((image, index) => {
            const item = createGalleryItem(image, currentResults.length + index);
            gallery.appendChild(item);
        });

        currentResults = data.images;

    } catch (error) {
        console.error('Error loading results:', error);
    }
}

// Create gallery item
function createGalleryItem(image, index) {
    const item = document.createElement('div');
    item.className = 'gallery-item';

    const img = document.createElement('img');
    img.src = `data:image/jpeg;base64,${image.image_data}`;
    img.alt = image.filename;

    const info = document.createElement('div');
    info.className = 'gallery-info';

    const filename = document.createElement('div');
    filename.className = 'gallery-filename';
    filename.textContent = image.filename;

    const stats = document.createElement('div');
    stats.className = 'gallery-stats';

    const birdStat = document.createElement('div');
    birdStat.className = 'gallery-stat';
    birdStat.innerHTML = `
        <span>🐦 Birds:</span>
        <span class="gallery-stat-value">${image.bird_count}</span>
    `;

    const timeStat = document.createElement('div');
    timeStat.className = 'gallery-stat';
    timeStat.innerHTML = `
        <span>⚡ Time:</span>
        <span class="gallery-stat-value">${image.inference_time.toFixed(2)}s</span>
    `;

    stats.appendChild(birdStat);
    stats.appendChild(timeStat);

    info.appendChild(filename);
    info.appendChild(stats);

    item.appendChild(img);
    item.appendChild(info);

    return item;
}

// Show summary
async function showSummary() {
    try {
        const response = await fetch('/status');
        const data = await response.json();

        // Update summary stats
        document.getElementById('summaryImages').textContent = data.current_image;
        document.getElementById('summaryBirds').textContent = data.total_birds;
        document.getElementById('summarySpeed').textContent = `${data.images_per_second.toFixed(2)} img/s`;
        document.getElementById('summaryTime').textContent = formatTime(data.elapsed_time);

        // Show summary section
        summarySection.style.display = 'flex';

        // Scroll to summary
        summarySection.scrollIntoView({ behavior: 'smooth', block: 'center' });

    } catch (error) {
        console.error('Error showing summary:', error);
    }
}

// Format time in seconds
function formatTime(seconds) {
    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    } else {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}m ${secs}s`;
    }
}

// Initialize
console.log('🍀 LuckyCharm ready!');
