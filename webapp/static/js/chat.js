/**
 * NestChat - Claude-Inspired Chat Interface
 * Handles SSE streaming, reasoning display, artifacts (tables, charts, maps)
 */

class NestChat {
    constructor() {
        this.messages = [];
        this.currentEventSource = null;
        this.conversationHistory = [];
        this.artifactIframes = [];

        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.clearBtn = document.getElementById('clear-chat-btn');
        this.downloadBtn = document.getElementById('download-chat-btn');

        this.setupEventListeners();
        this.autoResizeTextarea();

        // Listen for theme changes to update artifacts
        window.addEventListener('themechange', () => {
            this.updateArtifactThemes();
        });
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
         * Render an HTML artifact in an isolated iframe with theme-aware styling.
         */
        const artifactContainer = document.createElement('div');
        artifactContainer.className = 'artifact-container loading';
        artifactContainer.id = artifact.id;

        // Create skeleton loader
        const skeleton = document.createElement('div');
        skeleton.className = 'artifact-skeleton';
        skeleton.innerHTML = `
            <div class="skeleton-header"></div>
            <div class="skeleton-body">
                <div class="skeleton-bar"></div>
                <div class="skeleton-bar"></div>
                <div class="skeleton-bar"></div>
                <div class="skeleton-bar"></div>
            </div>
        `;
        artifactContainer.appendChild(skeleton);

        // Create header with fullscreen button
        const header = document.createElement('div');
        header.className = 'artifact-header';
        header.style.display = 'none'; // Hidden until loaded
        header.innerHTML = `
            <div class="artifact-title">Visualization</div>
            <button class="artifact-fullscreen-btn" title="Fullscreen">
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
                </svg>
            </button>
        `;

        // Create iframe for isolated rendering
        const iframe = document.createElement('iframe');
        iframe.className = 'artifact-iframe';
        iframe.sandbox = 'allow-scripts allow-same-origin';
        iframe.style.display = 'none'; // Hidden until loaded

        // Inject theme-aware styles into artifact HTML
        const themedHTML = this.injectThemeStyles(artifact.html);
        iframe.srcdoc = themedHTML;

        artifactContainer.appendChild(header);
        artifactContainer.appendChild(iframe);
        messageDiv.appendChild(artifactContainer);

        // Auto-adjust iframe height after load
        iframe.addEventListener('load', () => {
            // Remove loading state
            artifactContainer.classList.remove('loading');
            skeleton.remove();
            header.style.display = 'flex';
            iframe.style.display = 'block';

            try {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                const height = iframeDoc.body.scrollHeight;
                iframe.style.height = Math.min(height + 20, 600) + 'px';
            } catch (e) {
                // Cross-origin restrictions - use default height
                iframe.style.height = '500px';
            }
        });

        // Add fullscreen functionality
        const fullscreenBtn = header.querySelector('.artifact-fullscreen-btn');
        fullscreenBtn.addEventListener('click', () => {
            this.toggleArtifactFullscreen(artifactContainer, iframe);
        });

        // Store iframe reference for theme updates
        if (!this.artifactIframes) this.artifactIframes = [];
        this.artifactIframes.push(iframe);
    }

    toggleArtifactFullscreen(container, iframe) {
        if (container.classList.contains('fullscreen')) {
            // Exit fullscreen
            container.classList.remove('fullscreen');
            iframe.style.height = Math.min(iframe.contentDocument.body.scrollHeight + 20, 600) + 'px';

            // Update button icon
            const btn = container.querySelector('.artifact-fullscreen-btn');
            btn.innerHTML = `
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
                </svg>
            `;
        } else {
            // Enter fullscreen
            container.classList.add('fullscreen');
            iframe.style.height = 'calc(100vh - 120px)';

            // Update button icon to close
            const btn = container.querySelector('.artifact-fullscreen-btn');
            btn.innerHTML = `
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            `;
        }
    }

    injectThemeStyles(html) {
        /**
         * Inject theme CSS variables into artifact HTML so colors match UI theme.
         */
        const theme = document.documentElement.getAttribute('data-theme') || 'light';

        // Get current theme colors
        const styles = getComputedStyle(document.documentElement);
        const bgPrimary = styles.getPropertyValue('--bg-primary').trim();
        const bgSecondary = styles.getPropertyValue('--bg-secondary').trim();
        const textPrimary = styles.getPropertyValue('--text-primary').trim();
        const textSecondary = styles.getPropertyValue('--text-secondary').trim();
        const brandPrimary = styles.getPropertyValue('--brand-primary').trim();
        const accentCoastal = styles.getPropertyValue('--accent-coastal').trim();
        const accentOcean = styles.getPropertyValue('--accent-ocean').trim();
        const surfaceBase = styles.getPropertyValue('--surface-base').trim();
        const surfaceBorder = styles.getPropertyValue('--surface-border').trim();

        // Theme-aware style injection
        const themeStyles = `
            <style>
                :root {
                    --theme-bg-primary: ${bgPrimary};
                    --theme-bg-secondary: ${bgSecondary};
                    --theme-text-primary: ${textPrimary};
                    --theme-text-secondary: ${textSecondary};
                    --theme-brand: ${brandPrimary};
                    --theme-coastal: ${accentCoastal};
                    --theme-ocean: ${accentOcean};
                    --theme-surface: ${surfaceBase};
                    --theme-border: ${surfaceBorder};
                }
                body {
                    background: var(--theme-bg-primary, #fdfbf7) !important;
                    color: var(--theme-text-primary, #2a2520) !important;
                }
                h1, h2, h3, h4, h5, h6 {
                    color: var(--theme-text-primary, #2a2520) !important;
                }
                .card, .dashboard-card {
                    background: var(--theme-surface, #ffffff) !important;
                    border-color: var(--theme-border, rgba(101, 87, 68, 0.15)) !important;
                    color: var(--theme-text-primary, #2a2520) !important;
                }
                .metric-value {
                    color: var(--theme-text-primary, #2a2520) !important;
                }
                .metric-label {
                    color: var(--theme-text-secondary, #5c5247) !important;
                }
            </style>
        `;

        // Insert theme styles after <head> tag
        if (html.includes('<head>')) {
            return html.replace('<head>', '<head>' + themeStyles);
        } else if (html.includes('<html>')) {
            return html.replace('<html>', '<html><head>' + themeStyles + '</head>');
        } else {
            // No html/head tags - wrap entire content
            return `<!DOCTYPE html><html><head>${themeStyles}</head><body>${html}</body></html>`;
        }
    }

    updateArtifactThemes() {
        /**
         * Update all artifact iframes when theme changes.
         */
        if (!this.artifactIframes) return;

        this.artifactIframes.forEach(iframe => {
            try {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                const theme = document.documentElement.getAttribute('data-theme') || 'light';

                // Get current theme colors
                const styles = getComputedStyle(document.documentElement);

                // Update CSS variables in iframe
                const root = iframeDoc.documentElement;
                root.style.setProperty('--theme-bg-primary', styles.getPropertyValue('--bg-primary'));
                root.style.setProperty('--theme-bg-secondary', styles.getPropertyValue('--bg-secondary'));
                root.style.setProperty('--theme-text-primary', styles.getPropertyValue('--text-primary'));
                root.style.setProperty('--theme-text-secondary', styles.getPropertyValue('--text-secondary'));
                root.style.setProperty('--theme-brand', styles.getPropertyValue('--brand-primary'));
                root.style.setProperty('--theme-coastal', styles.getPropertyValue('--accent-coastal'));
                root.style.setProperty('--theme-ocean', styles.getPropertyValue('--accent-ocean'));
                root.style.setProperty('--theme-surface', styles.getPropertyValue('--surface-base'));
                root.style.setProperty('--theme-border', styles.getPropertyValue('--surface-border'));
            } catch (e) {
                console.warn('Could not update artifact theme:', e);
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
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 0.75em; color: #888; display: flex; align-items: center; gap: 4px;">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="12" r="3"/></svg>
                        ${lat.toFixed(4)}, ${lon.toFixed(4)}
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

        // Count figures and tables for proper numbering
        let figureNum = 1;
        let tableNum = 1;

        const today = new Date();
        const dateString = today.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
        const yearString = today.getFullYear();

        let html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NestChat Research Analysis - ${new Date().toLocaleDateString()}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        /* ============================================
           RESEARCH ARTICLE STYLING
           Professional publication-quality formatting
           ============================================ */

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        @page {
            size: letter;
            margin: 1in;
        }

        body {
            font-family: 'Georgia', 'Palatino', 'Times New Roman', serif;
            background: #ffffff;
            color: #1a1a1a;
            line-height: 1.8;
            font-size: 12pt;
            padding: 0;
            margin: 0;
        }

        .document {
            max-width: 8.5in;
            margin: 0 auto;
            background: white;
            padding: 1in;
            min-height: 100vh;
        }

        /* ===== TITLE PAGE ===== */
        .title-page {
            text-align: center;
            padding: 2in 0 1in 0;
            margin-bottom: 1in;
            border-bottom: 3px double #333;
            page-break-after: always;
        }

        .title-page h1 {
            font-size: 20pt;
            font-weight: bold;
            margin-bottom: 0.5in;
            color: #1a1a1a;
            line-height: 1.3;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .title-page .subtitle {
            font-size: 14pt;
            font-style: italic;
            color: #555;
            margin-bottom: 0.75in;
        }

        .title-page .authors {
            font-size: 11pt;
            margin-bottom: 0.25in;
            font-weight: 600;
        }

        .title-page .affiliation {
            font-size: 10pt;
            color: #666;
            margin-bottom: 0.5in;
            font-style: italic;
        }

        .title-page .date {
            font-size: 11pt;
            color: #333;
            margin-top: 0.5in;
        }

        /* ===== ABSTRACT ===== */
        .abstract {
            margin: 1.5em 0 2em 0;
            padding: 1.5em;
            background: #f9f9f9;
            border-left: 4px solid #7BABAE;
        }

        .abstract-title {
            font-size: 12pt;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.75em;
            color: #1a1a1a;
        }

        .abstract-content {
            font-size: 10.5pt;
            text-align: justify;
            line-height: 1.6;
        }

        /* ===== SECTIONS ===== */
        .section {
            margin: 2em 0;
        }

        .section-number {
            font-weight: bold;
            color: #7BABAE;
        }

        h2 {
            font-size: 14pt;
            font-weight: bold;
            margin: 1.5em 0 0.75em 0;
            color: #1a1a1a;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 0.25em;
        }

        h3 {
            font-size: 12pt;
            font-weight: bold;
            margin: 1.25em 0 0.5em 0;
            color: #333;
        }

        /* ===== QUESTION/ANSWER PAIRS ===== */
        .qa-pair {
            margin: 2em 0;
            page-break-inside: avoid;
        }

        .question {
            font-weight: bold;
            font-size: 11pt;
            color: #1a1a1a;
            margin-bottom: 0.75em;
            padding: 0.75em 1em;
            background: #f5f5f5;
            border-left: 4px solid #7BABAE;
            font-style: italic;
        }

        .question::before {
            content: "QUERY: ";
            font-weight: bold;
            color: #7BABAE;
            font-style: normal;
            letter-spacing: 0.5px;
        }

        .answer {
            margin-left: 1em;
            text-align: justify;
            font-size: 11pt;
            line-height: 1.7;
        }

        .answer p {
            margin-bottom: 1em;
        }

        .answer ul, .answer ol {
            margin: 1em 0 1em 2em;
        }

        .answer li {
            margin-bottom: 0.5em;
        }

        .answer code {
            font-family: 'Courier New', monospace;
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10pt;
        }

        .answer strong {
            font-weight: 600;
            color: #1a1a1a;
        }

        /* ===== FIGURES & TABLES ===== */
        .figure-container,
        .table-container {
            margin: 2em 0;
            page-break-inside: avoid;
            text-align: center;
        }

        .figure-caption,
        .table-caption {
            font-size: 10pt;
            margin-top: 0.75em;
            text-align: center;
            color: #333;
        }

        .figure-caption strong,
        .table-caption strong {
            font-weight: bold;
            color: #1a1a1a;
        }

        .data-table {
            width: 100%;
            margin: 1em auto;
            border-collapse: collapse;
            font-size: 9pt;
            max-width: 100%;
            background: white;
        }

        .data-table th {
            background: #f8f8f8;
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
            border-top: 2px solid #333;
            border-bottom: 1px solid #333;
            color: #1a1a1a;
        }

        .data-table td {
            padding: 8px 12px;
            border-bottom: 1px solid #ddd;
            color: #333;
        }

        .data-table tbody tr:hover {
            background: #f9f9f9;
        }

        .artifact-iframe {
            width: 100%;
            border: 1px solid #ddd;
            margin: 1em 0;
            background: white;
        }

        /* ===== FOOTER ===== */
        .document-footer {
            margin-top: 3in;
            padding-top: 1em;
            border-top: 2px solid #333;
            text-align: center;
            font-size: 9pt;
            color: #666;
        }

        .document-footer .logo {
            font-weight: bold;
            font-size: 11pt;
            color: #7BABAE;
            margin-bottom: 0.5em;
        }

        /* ===== PRINT STYLES ===== */
        @media print {
            body {
                font-size: 11pt;
            }

            .document {
                padding: 0;
                max-width: 100%;
            }

            .qa-pair,
            .figure-container,
            .table-container {
                page-break-inside: avoid;
            }

            h2 {
                page-break-after: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="document">

        <!-- TITLE PAGE -->
        <div class="title-page">
            <h1>NestChat Research Analysis</h1>
            <div class="subtitle">AI-Powered Avian Intelligence Report</div>
            <div class="authors">Generated by NestScope Intelligence System</div>
            <div class="affiliation">Gulf Coast Avian Monitoring Platform<br>Data Period: 2010-2021</div>
            <div class="date">${dateString}</div>
        </div>

        <!-- ABSTRACT -->
        <div class="abstract">
            <div class="abstract-title">Abstract</div>
            <div class="abstract-content">
                This report presents an AI-assisted analysis of Gulf Coast avian data spanning 2010-2021,
                covering 592 colonial waterbird nesting sites across five states (Texas, Louisiana, Mississippi,
                Alabama, and Florida). The analysis was conducted using NestChat, an intelligent query system
                powered by natural language processing and automated SQL generation. This document contains
                ${messages.length / 2} query-response pairs, including data visualizations and statistical summaries
                generated through conversational interaction with the NestScope database.
            </div>
        </div>

        <!-- MAIN CONTENT -->
        <h2><span class="section-number">1.</span> Analysis & Results</h2>
        `;

        // Generate Q&A pairs
        let questionNum = 1;
        for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];
            const isUser = msg.classList.contains('user');

            if (isUser) {
                const contentDiv = msg.querySelector('.message-content');
                const question = contentDiv ? contentDiv.textContent.trim() : '';

                html += `
        <div class="qa-pair">
            <div class="question">${this.escapeHtml(question)}</div>`;

                // Get the next message (assistant response)
                if (i + 1 < messages.length) {
                    i++; // Move to assistant message
                    const assistantMsg = messages[i];
                    const answerDiv = assistantMsg.querySelector('.message-content');
                    const answer = answerDiv ? answerDiv.innerHTML : '';

                    html += `
            <div class="answer">
                ${answer}
            </div>`;

                    // Include data tables with captions
                    const tables = assistantMsg.querySelectorAll('.data-table');
                    tables.forEach((table) => {
                        html += `
            <div class="table-container">
                ${table.outerHTML}
                <div class="table-caption">
                    <strong>Table ${tableNum}.</strong> Query results showing data extracted from the NestScope database.
                </div>
            </div>`;
                        tableNum++;
                    });

                    // Include artifacts (charts) with captions
                    const artifacts = assistantMsg.querySelectorAll('.artifact-iframe');
                    artifacts.forEach((iframe) => {
                        const artifactHTML = iframe.srcdoc;
                        html += `
            <div class="figure-container">
                <div style="max-width: 100%; margin: 0 auto;">
                    ${artifactHTML}
                </div>
                <div class="figure-caption">
                    <strong>Figure ${figureNum}.</strong> Data visualization generated from query results.
                </div>
            </div>`;
                        figureNum++;
                    });
                }

                html += `
        </div>`;
                questionNum++;
            }
        }

        // FOOTER
        html += `
        <div class="document-footer">
            <div class="logo">NestScope</div>
            <div>AI-Powered Gulf Coast Avian Intelligence Platform</div>
            <div>Report Generated: ${dateString}</div>
            <div style="margin-top: 1em; font-size: 8pt; color: #999;">
                This report was automatically generated by NestChat using Claude AI and the NestScope database.<br>
                For more information, visit the NestScope project documentation.
            </div>
        </div>

    </div>
</body>
</html>`;

        const blob = new Blob([html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `nestchat-research-${new Date().toISOString().split('T')[0]}.html`;
        a.click();
        URL.revokeObjectURL(url);

        showToast('Research report downloaded! Open in browser or print to PDF.', 'success');
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
