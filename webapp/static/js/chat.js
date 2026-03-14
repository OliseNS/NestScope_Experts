/**
 * NestChat - Claude-Inspired Chat Interface
 * Handles SSE streaming, reasoning display, artifacts (tables, charts, maps)
 */

class NestChat {
    constructor() {
        this.messages = [];
        this.currentEventSource = null;
        this.conversationHistory = [];

        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.clearBtn = document.getElementById('clear-chat-btn');
        this.downloadBtn = document.getElementById('download-chat-btn');

        this.setupEventListeners();
        this.autoResizeTextarea();
    }

    setupEventListeners() {
        // Send message
        this.sendBtn.addEventListener('click', () => this.sendMessage());

        // Enter to send, Shift+Enter for new line
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        this.chatInput.addEventListener('input', () => this.autoResizeTextarea());

        // Clear chat
        this.clearBtn.addEventListener('click', () => this.clearChat());

        // Download chat
        this.downloadBtn.addEventListener('click', () => this.downloadChat());

        // Example prompts
        document.querySelectorAll('.example-prompt').forEach(btn => {
            btn.addEventListener('click', () => {
                const prompt = btn.getAttribute('data-prompt');
                this.chatInput.value = prompt;
                this.sendMessage();
            });
        });
    }

    autoResizeTextarea() {
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 200) + 'px';
    }

    async sendMessage() {
        const question = this.chatInput.value.trim();

        // Prevent sending if empty or already streaming
        if (!question) {
            console.log('Empty message, not sending');
            return;
        }

        if (this.currentEventSource !== null) {
            console.log('Already streaming, waiting...');
            return;
        }

        // Mark as streaming
        this.currentEventSource = true;

        // Hide welcome if first message
        const welcomeSection = document.querySelector('.welcome-section');
        if (welcomeSection) {
            welcomeSection.remove();
        }

        // Add user message
        this.addUserMessage(question);

        // Clear input
        this.chatInput.value = '';
        this.autoResizeTextarea();

        // Disable input while processing
        this.setInputState(false);

        // Add assistant message placeholder
        const messageDiv = this.addAssistantMessage();

        // Start streaming
        try {
            await this.streamResponse(question, messageDiv);
        } catch (error) {
            console.error('Send message error:', error);
            this.setInputState(true);
            this.currentEventSource = null;
        }
    }

    addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        messageDiv.innerHTML = `
            <div class="message-content">${this.escapeHtml(text)}</div>
        `;
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();

        // Add to conversation history
        this.conversationHistory.push({
            role: 'user',
            content: text
        });

        return messageDiv;
    }

    addAssistantMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';
        messageDiv.innerHTML = `
            <div class="thinking-indicator">
                <span>Thinking</span>
                <div class="thinking-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
            <div class="message-content" style="display: none;"></div>
        `;
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        return messageDiv;
    }

    async streamResponse(question, messageDiv) {
        const thinkingIndicator = messageDiv.querySelector('.thinking-indicator');
        const contentDiv = messageDiv.querySelector('.message-content');

        let fullAnswer = '';
        let sqlQuery = '';
        let results = null;
        let thinkingSteps = [];

        try {
            // Use fetch with POST to send conversation history
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question: question,
                    conversation_history: this.conversationHistory
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            const processStream = async () => {
                try {
                    while (true) {
                        const { done, value } = await reader.read();

                        if (done) {
                            // Stream ended - ensure input is re-enabled
                            this.setInputState(true);
                            this.currentEventSource = null;
                            break;
                        }

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop(); // Keep incomplete line in buffer

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const data = line.slice(6);
                                try {
                                    const event = JSON.parse(data);
                                    this.handleStreamEvent(event, messageDiv, thinkingIndicator, contentDiv, {
                                        fullAnswer,
                                        sqlQuery,
                                        results,
                                        thinkingSteps
                                    });

                                    // Update references
                                    if (event.type === 'answer_chunk') {
                                        fullAnswer += event.content;
                                    } else if (event.type === 'sql_query' || event.type === 'sql_generated') {
                                        sqlQuery = event.content;
                                    } else if (event.type === 'results') {
                                        results = event.content;
                                    } else if (event.type === 'thinking_step' || event.type === 'question_analysis' || event.type === 'validation_result') {
                                        // Collect all thinking/reasoning steps
                                        if (event.content) {
                                            thinkingSteps.push(event.content);
                                        } else if (event.reasoning) {
                                            thinkingSteps.push(event.reasoning);
                                        }
                                    } else if (event.type === 'answer_end') {
                                        if (event.clean_answer) {
                                            fullAnswer = event.clean_answer;
                                        }

                                        // Parse and extract artifacts from answer
                                        const { cleanAnswer, artifacts } = this.parseArtifacts(fullAnswer);
                                        contentDiv.innerHTML = this.formatMarkdown(cleanAnswer);

                                        // Add to conversation history (without artifact blocks)
                                        this.conversationHistory.push({
                                            role: 'assistant',
                                            content: cleanAnswer
                                        });

                                        // Add reasoning section
                                        if (thinkingSteps.length > 0 || sqlQuery) {
                                            this.addReasoningSection(messageDiv, thinkingSteps, sqlQuery);
                                        }

                                        // Render HTML artifacts (charts only - NOT maps)
                                        if (artifacts && artifacts.length > 0) {
                                            artifacts.forEach(artifact => {
                                                this.renderArtifact(messageDiv, artifact);
                                            });
                                        }

                                        // Render data table (always show raw data)
                                        if (results && results.length > 0) {
                                            this.renderDataTable(messageDiv, results);
                                        }

                                        // Render map using Leaflet (traditional method)
                                        if (results && results.length > 0) {
                                            this.renderMap(messageDiv, results);
                                        }
                                    } else if (event.type === 'done') {
                                        // Re-enable input
                                        this.setInputState(true);
                                        this.currentEventSource = null;
                                    }
                                } catch (e) {
                                    console.error('Error parsing SSE data:', e, data);
                                }
                            }
                        }
                    }
                } catch (error) {
                    console.error('Stream reading error:', error);
                    this.handleStreamError(messageDiv, thinkingIndicator, contentDiv, error);
                }
            };

            await processStream();

        } catch (error) {
            console.error('Stream error:', error);
            this.handleStreamError(messageDiv, thinkingIndicator, contentDiv, error);
        }
    }

    handleStreamEvent(event, messageDiv, thinkingIndicator, contentDiv, state) {
        switch (event.type) {
            case 'thinking_step':
            case 'question_analysis':
            case 'validation_result':
                // These are handled in the reasoning section
                break;

            case 'sql_generated':
            case 'sql_query':
                // Handled in main loop
                break;

            case 'results':
                // Handled in main loop
                break;

            case 'answer_start':
                thinkingIndicator.style.display = 'none';
                contentDiv.style.display = 'block';
                break;

            case 'answer_chunk':
                // Update content as it streams, but hide artifact code blocks
                const streamingText = state.fullAnswer + event.content;
                const displayText = this.hideArtifactsDuringStreaming(streamingText);
                contentDiv.innerHTML = this.formatMarkdown(displayText);
                this.scrollToBottom();
                break;

            case 'answer_end':
                // Handled in main loop
                break;

            case 'query_error':
                contentDiv.innerHTML = `<div style="color: #F04438;">Query error: ${this.escapeHtml(event.content)}</div>`;
                contentDiv.style.display = 'block';
                thinkingIndicator.style.display = 'none';
                break;

            case 'error':
                this.handleStreamError(messageDiv, thinkingIndicator, contentDiv, new Error(event.content));
                break;

            case 'done':
                // Handled in main loop
                break;
        }
    }

    handleStreamError(messageDiv, thinkingIndicator, contentDiv, error) {
        console.error('Stream error:', error);
        messageDiv.classList.add('message-error');
        contentDiv.innerHTML = `Error: ${this.escapeHtml(error.message)}<br><small>Please make sure the backend is running.</small>`;
        thinkingIndicator.style.display = 'none';
        contentDiv.style.display = 'block';
        this.setInputState(true);
        this.currentEventSource = null;
    }

    addReasoningSection(messageDiv, thinkingSteps, sqlQuery) {
        const reasoningDiv = document.createElement('div');
        reasoningDiv.className = 'reasoning-section';

        let stepsHTML = '';
        if (thinkingSteps.length > 0) {
            stepsHTML = thinkingSteps.map(step =>
                `<div class="reasoning-step">${this.escapeHtml(step)}</div>`
            ).join('');
        }

        if (sqlQuery) {
            stepsHTML += `
                <div class="reasoning-step">
                    <strong>SQL Query:</strong><br>
                    <code>${this.escapeHtml(sqlQuery)}</code>
                </div>
            `;
        }

        reasoningDiv.innerHTML = `
            <div class="reasoning-header">
                <div class="reasoning-title">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                    </svg>
                    <span>Show reasoning</span>
                </div>
                <div class="reasoning-toggle">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                    </svg>
                </div>
            </div>
            <div class="reasoning-content">
                <div class="reasoning-steps">
                    ${stepsHTML}
                </div>
            </div>
        `;

        // Toggle functionality
        const header = reasoningDiv.querySelector('.reasoning-header');
        header.addEventListener('click', () => {
            reasoningDiv.classList.toggle('expanded');
        });

        messageDiv.appendChild(reasoningDiv);
    }

    hideArtifactsDuringStreaming(text) {
        /**
         * Replace artifact blocks with loading animations during streaming.
         * This prevents users from seeing raw HTML code.
         */
        const artifactRegex = /```artifact\n([\s\S]*?)(?:```|$)/g;

        let artifactCount = 0;
        const textWithPlaceholders = text.replace(artifactRegex, (match) => {
            artifactCount++;
            return `\n\n<div class="artifact-loading" data-artifact-index="${artifactCount}">
                <div class="artifact-loading-content">
                    <div class="artifact-loading-spinner"></div>
                    <div class="artifact-loading-text">Creating visualization...</div>
                </div>
            </div>\n\n`;
        });

        return textWithPlaceholders;
    }

    parseArtifacts(text) {
        /**
         * Parse artifact blocks from AI response.
         * Artifacts are wrapped in ```artifact blocks.
         * Returns: { cleanAnswer: string, artifacts: array }
         */
        const artifacts = [];
        const artifactRegex = /```artifact\n([\s\S]*?)```/g;

        let match;
        let cleanAnswer = text;

        // Extract all artifacts
        while ((match = artifactRegex.exec(text)) !== null) {
            artifacts.push({
                html: match[1].trim(),
                id: 'artifact-' + Date.now() + '-' + artifacts.length
            });
        }

        // Remove artifact blocks from answer
        cleanAnswer = text.replace(artifactRegex, '').trim();

        return { cleanAnswer, artifacts };
    }

    renderArtifact(messageDiv, artifact) {
        /**
         * Render an HTML artifact in an isolated iframe.
         */
        const artifactContainer = document.createElement('div');
        artifactContainer.className = 'artifact-container';
        artifactContainer.id = artifact.id;

        // Create iframe for isolated rendering
        const iframe = document.createElement('iframe');
        iframe.className = 'artifact-iframe';
        iframe.sandbox = 'allow-scripts allow-same-origin';
        iframe.srcdoc = artifact.html;

        artifactContainer.appendChild(iframe);
        messageDiv.appendChild(artifactContainer);

        // Auto-adjust iframe height after load
        iframe.addEventListener('load', () => {
            try {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                const height = iframeDoc.body.scrollHeight;
                iframe.style.height = Math.min(height + 20, 600) + 'px';
            } catch (e) {
                // Cross-origin restrictions - use default height
                iframe.style.height = '500px';
            }
        });
    }

    renderDataTable(messageDiv, data) {
        if (!data || data.length === 0) return;

        const tableContainer = document.createElement('div');
        tableContainer.className = 'data-table-container';

        const tableId = 'table-' + Date.now();
        const columns = Object.keys(data[0]);

        tableContainer.innerHTML = `
            <div class="data-table-header">
                <div class="data-table-title">Data Results (${data.length} rows)</div>
                <div class="table-actions">
                    <button class="table-btn" onclick="nestChat.downloadCSV('${tableId}')">
                        <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display: inline; vertical-align: middle; margin-right: 4px;">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                        </svg>
                        CSV
                    </button>
                </div>
            </div>
            <div class="data-table-scroll">
                <table class="data-table" id="${tableId}">
                    <thead>
                        <tr>
                            ${columns.map(col => `<th>${this.escapeHtml(col)}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${data.map(row => `
                            <tr>
                                ${columns.map(col => `<td>${this.escapeHtml(String(row[col] ?? ''))}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        messageDiv.appendChild(tableContainer);
    }

    renderMap(messageDiv, data) {
        if (!data || data.length === 0) return;

        // Check for latitude/longitude columns
        const hasCoords = data.some(row =>
            (row.Latitude || row.latitude) && (row.Longitude || row.longitude)
        );

        if (!hasCoords) return;

        // Create map container
        const mapContainer = document.createElement('div');
        mapContainer.className = 'map-container';
        const mapId = 'map-' + Date.now();
        mapContainer.id = mapId;

        // Add fullscreen button
        const fullscreenBtn = document.createElement('button');
        fullscreenBtn.className = 'map-fullscreen-btn';
        fullscreenBtn.innerHTML = `
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
            </svg>
        `;
        fullscreenBtn.title = 'Toggle fullscreen';
        mapContainer.appendChild(fullscreenBtn);

        messageDiv.appendChild(mapContainer);

        // Render map
        setTimeout(() => {
            const validCoords = data.filter(row => {
                const lat = parseFloat(row.Latitude || row.latitude);
                const lon = parseFloat(row.Longitude || row.longitude);
                return !isNaN(lat) && !isNaN(lon);
            });

            if (validCoords.length === 0) return;

            // Calculate center
            const avgLat = validCoords.reduce((sum, row) =>
                sum + parseFloat(row.Latitude || row.latitude), 0) / validCoords.length;
            const avgLon = validCoords.reduce((sum, row) =>
                sum + parseFloat(row.Longitude || row.longitude), 0) / validCoords.length;

            // Initialize map
            const map = L.map(mapId).setView([avgLat, avgLon], 7);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);

            // Add markers with rich popups
            validCoords.forEach(row => {
                const lat = parseFloat(row.Latitude || row.latitude);
                const lon = parseFloat(row.Longitude || row.longitude);

                // Build popup HTML with ALL data from the row
                let popupHTML = '<div style="min-width: 200px; max-width: 300px;">';

                // Get all columns except Lat/Lon
                const columns = Object.keys(row).filter(col =>
                    !['Latitude', 'latitude', 'Longitude', 'longitude'].includes(col)
                );

                // Add each field to popup
                columns.forEach(col => {
                    const value = row[col];
                    if (value !== null && value !== undefined && value !== '') {
                        // Format column name (remove underscores, capitalize)
                        const displayName = col
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, l => l.toUpperCase());

                        // Format value
                        let displayValue = value;
                        if (typeof value === 'number') {
                            displayValue = value.toLocaleString();
                        }

                        // Add to popup with nice formatting
                        if (col === 'ColonyName' || col.toLowerCase().includes('name')) {
                            popupHTML += `<div style="font-size: 1.1em; font-weight: 600; margin-bottom: 8px; color: #7BABAE;">${displayValue}</div>`;
                        } else {
                            popupHTML += `
                                <div style="margin: 6px 0; padding: 4px 0; border-bottom: 1px solid #eee;">
                                    <div style="font-size: 0.75em; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">${displayName}</div>
                                    <div style="font-size: 0.95em; font-weight: 500; color: #333; margin-top: 2px;">${displayValue}</div>
                                </div>
                            `;
                        }
                    }
                });

                // Add coordinates at the bottom
                popupHTML += `
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 0.75em; color: #888;">
                        📍 ${lat.toFixed(4)}, ${lon.toFixed(4)}
                    </div>
                `;

                popupHTML += '</div>';

                L.circleMarker([lat, lon], {
                    radius: 8,
                    fillColor: '#7BABAE',
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }).bindPopup(popupHTML, {
                    maxWidth: 350,
                    className: 'custom-popup'
                }).addTo(map);
            });

            // Fullscreen toggle
            let isFullscreen = false;
            fullscreenBtn.addEventListener('click', () => {
                isFullscreen = !isFullscreen;
                mapContainer.classList.toggle('fullscreen');

                // Update button icon
                if (isFullscreen) {
                    fullscreenBtn.innerHTML = `
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    `;
                    fullscreenBtn.title = 'Exit fullscreen';
                } else {
                    fullscreenBtn.innerHTML = `
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
                        </svg>
                    `;
                    fullscreenBtn.title = 'Toggle fullscreen';
                }

                // Invalidate map size to fix rendering issues
                setTimeout(() => map.invalidateSize(), 100);
            });
        }, 100);
    }

    downloadCSV(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;

        let csv = '';
        const rows = table.querySelectorAll('tr');

        rows.forEach(row => {
            const cols = row.querySelectorAll('td, th');
            const rowData = Array.from(cols).map(col => {
                let data = col.textContent;
                // Escape quotes and wrap in quotes if contains comma
                data = data.replace(/"/g, '""');
                if (data.includes(',') || data.includes('\n')) {
                    data = `"${data}"`;
                }
                return data;
            });
            csv += rowData.join(',') + '\n';
        });

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `nestchat-data-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);

        showToast('CSV downloaded successfully', 'success');
    }

    clearChat() {
        if (!confirm('Clear all messages?')) return;

        // Remove all messages
        const messages = this.chatMessages.querySelectorAll('.message, .welcome-section');
        messages.forEach(msg => msg.remove());

        // Re-add welcome section
        const welcomeSection = document.createElement('div');
        welcomeSection.className = 'welcome-section';
        welcomeSection.innerHTML = `
            <h2 class="welcome-title">Ask me anything about Gulf Coast bird data</h2>
            <p class="welcome-subtitle">11 years • 592 colonies • 73 species • 2010-2021</p>
            <div class="example-prompts">
                <button class="example-prompt" data-prompt="Show the total bird count for Brown Pelican from 2015 to 2021">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"/>
                    </svg>
                    Brown Pelican population trends 2015-2021
                </button>
                <button class="example-prompt" data-prompt="What were the top 5 species by bird count in 2021?">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 00 2-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                    </svg>
                    Top 5 species by count in 2021
                </button>
                <button class="example-prompt" data-prompt="List all bird colonies in Louisiana with their coordinates">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
                    </svg>
                    Louisiana colonies with coordinates
                </button>
                <button class="example-prompt" data-prompt="Which colonies had decreasing bird counts over time?">
                    <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"/>
                    </svg>
                    Colonies with declining populations
                </button>
            </div>
        `;
        this.chatMessages.appendChild(welcomeSection);

        // Re-setup example prompt listeners
        welcomeSection.querySelectorAll('.example-prompt').forEach(btn => {
            btn.addEventListener('click', () => {
                const prompt = btn.getAttribute('data-prompt');
                this.chatInput.value = prompt;
                this.sendMessage();
            });
        });

        // Clear conversation history
        this.conversationHistory = [];

        showToast('Chat cleared', 'success');
    }

    downloadChat() {
        const messages = Array.from(this.chatMessages.querySelectorAll('.message'));
        if (messages.length === 0) {
            showToast('No messages to download', 'info');
            return;
        }

        let html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NestChat Conversation - ${new Date().toLocaleDateString()}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            background: white;
            color: #1a1a1a;
            line-height: 1.7;
            padding: 40px 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            padding-bottom: 32px;
            margin-bottom: 48px;
            border-bottom: 1px solid #e0e0e0;
        }
        .header h1 {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 8px;
            color: #1a1a1a;
        }
        .header .meta {
            font-size: 0.9rem;
            color: #666;
        }
        .message {
            margin-bottom: 40px;
        }
        .message-author {
            font-weight: 600;
            font-size: 0.875rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .message-content {
            color: #1a1a1a;
            font-size: 1rem;
        }
        .message-content p {
            margin-bottom: 16px;
        }
        .message-content h1,
        .message-content h2,
        .message-content h3 {
            color: #1a1a1a;
            margin: 24px 0 16px 0;
            font-weight: 600;
        }
        .message-content h1 { font-size: 1.5rem; }
        .message-content h2 { font-size: 1.25rem; }
        .message-content h3 { font-size: 1.1rem; }
        .message-content code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9em;
        }
        .message-content ul,
        .message-content ol {
            margin-left: 24px;
            margin-bottom: 16px;
        }
        .message-content li {
            margin-bottom: 8px;
        }
        .data-table {
            width: 100%;
            margin: 24px 0;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        .data-table th {
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #ddd;
        }
        .data-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }
        .artifact-content {
            margin: 24px 0;
        }
        .footer {
            text-align: center;
            padding-top: 40px;
            margin-top: 60px;
            border-top: 1px solid #e0e0e0;
            color: #666;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NestChat Conversation</h1>
            <div class="meta">${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</div>
        </div>
        `;

        messages.forEach(msg => {
            const isUser = msg.classList.contains('user');
            const author = isUser ? 'You' : 'NestChat';
            const contentDiv = msg.querySelector('.message-content');
            const content = contentDiv ? contentDiv.innerHTML : '';

            html += `
            <div class="message">
                <div class="message-author">${author}</div>
                <div class="message-content">
                    ${content}
                </div>
            `;

            // Include data tables
            const tables = msg.querySelectorAll('.data-table');
            tables.forEach((table) => {
                html += `<div class="artifact-content">${table.outerHTML}</div>`;
            });

            // Include artifacts (iframes)
            const artifacts = msg.querySelectorAll('.artifact-iframe');
            artifacts.forEach((iframe) => {
                const artifactHTML = iframe.srcdoc;
                html += `<div class="artifact-content">${artifactHTML}</div>`;
            });

            html += `</div>`;
        });

        html += `
        <div class="footer">
            NestScope - AI-Powered Gulf Coast Avian Intelligence
        </div>
    </div>
</body>
</html>
        `;

        const blob = new Blob([html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `nestchat-${new Date().toISOString().split('T')[0]}.html`;
        a.click();
        URL.revokeObjectURL(url);

        showToast('Conversation downloaded! Open the HTML file in any browser.', 'success');
    }

    setInputState(enabled) {
        this.chatInput.disabled = !enabled;
        this.sendBtn.disabled = !enabled;

        if (enabled) {
            // Focus on input when enabled
            this.chatInput.focus();
            console.log('Input enabled');
        } else {
            console.log('Input disabled');
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    getChartColor(index, alpha = 1) {
        const colors = [
            `rgba(123, 171, 174, ${alpha})`,  // Coastal
            `rgba(217, 119, 87, ${alpha})`,   // Claude orange
            `rgba(83, 124, 138, ${alpha})`,   // Ocean
        ];
        return colors[index % colors.length];
    }

    formatMarkdown(text) {
        // Configure marked.js with syntax highlighting
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false,
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(code, { language: lang }).value;
                    } catch (err) {}
                }
                try {
                    return hljs.highlightAuto(code).value;
                } catch (err) {}
                return code;
            }
        });

        // Use marked.js to parse markdown
        const html = marked.parse(text);

        // After rendering, highlight any code blocks that weren't caught
        setTimeout(() => {
            document.querySelectorAll('pre code:not(.hljs)').forEach((block) => {
                hljs.highlightElement(block);
            });
        }, 10);

        return html;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat
const nestChat = new NestChat();
