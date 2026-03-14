# Artifact Rendering Flow - Debug Reference

## 🔍 Complete Technical Flow

This document traces the exact path of artifact rendering from backend to frontend for debugging.

---

## Backend: Artifact Generation

### 1. User Question Arrives
**Endpoint:** `POST /ask/agentic/stream`
**File:** `server/main.py:2706`

```python
@app.post("/ask/agentic/stream")
async def ask_question_agentic_stream(request: QuestionRequest):
    async for event in agentic_chatbot.agentic_ask_stream(request.question, ...):
        yield f"data: {json.dumps(event)}\n\n"
```

### 2. Agentic Processing
**Function:** `agentic_ask_stream()`
**File:** `server/main.py:1720`

**Steps:**
1. Analyze question → `_analyze_question()`
2. Generate SQL → `generate_sql_query()`
3. Validate SQL → `_validate_sql()`
4. Execute query → `execute_query()`
5. Validate results → `_validate_results()`
6. **Generate answer with artifacts** → `generate_answer_stream()`

### 3. Answer Generation with Artifacts
**Function:** `generate_answer_stream()`
**File:** `server/main.py:1359`

**System Prompt Includes (lines 1386-1597):**
```
## CRITICAL: HTML ARTIFACT GENERATION

**Generate artifacts for charts and trends. Maps are handled automatically by the system.**

### When to Create Artifacts:
- ✅ Time-series data → Line chart artifact
- ✅ Category comparisons → Bar chart artifact
- ❌ Geographic data → NO artifact, map auto-generates

### Artifact Format:
```artifact
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
    ...
</head>
<body>
    <h3>Chart Title</h3>
    <canvas id="myChart"></canvas>
    <script>
        new Chart(document.getElementById('myChart'), { ... });
    </script>
</body>
</html>
```
```

**Streaming:**
```python
# Line 1622-1632
stream = client.chat.completions.create(
    model=self.model,
    messages=messages,
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        yield chunk.choices[0].delta.content  # Streams character by character
```

### 4. Events Yielded to Frontend
**File:** `server/main.py:1906-1935`

```python
# Start answer streaming
yield {'type': 'answer_start'}

# Stream answer chunks (including artifact code)
full_answer = ""
for chunk in self.generate_answer_stream(...):
    full_answer += chunk
    yield {'type': 'answer_chunk', 'content': chunk}  # Each character/word

# When complete, send full answer WITH artifacts intact
yield {
    'type': 'answer_end',
    'clean_answer': full_answer  # IMPORTANT: Artifacts NOT stripped here!
}

yield {'type': 'done'}
```

**Key Point:** Backend does NOT strip artifacts - it sends the complete response including ` ```artifact...``` ` blocks.

---

## Frontend: Artifact Handling

### 5. SSE Stream Reception
**Function:** `sendMessage()`
**File:** `webapp/static/js/chat.js:127`

```javascript
// Line 151-161: POST request to /api/chat/stream
const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        question: question,
        conversation_history: this.conversationHistory
    })
});

// Line 167-169: Read SSE stream
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';
```

### 6. Event Processing Loop
**File:** `webapp/static/js/chat.js:187-258`

```javascript
for (const line of lines) {
    if (line.startsWith('data: ')) {
        const data = line.slice(6);
        const event = JSON.parse(data);

        // Route to event handler
        this.handleStreamEvent(event, messageDiv, thinkingIndicator, contentDiv, state);

        // Track state
        if (event.type === 'answer_chunk') {
            fullAnswer += event.content;  // Accumulate complete answer
        }
    }
}
```

### 7. Hiding Artifacts During Streaming
**Function:** `handleStreamEvent()` → `hideArtifactsDuringStreaming()`
**File:** `webapp/static/js/chat.js:296-301`

```javascript
case 'answer_chunk':
    // Update content as it streams, but hide artifact code blocks
    const streamingText = state.fullAnswer + event.content;
    const displayText = this.hideArtifactsDuringStreaming(streamingText);
    contentDiv.innerHTML = this.formatMarkdown(displayText);
    this.scrollToBottom();
    break;
```

**Function:** `hideArtifactsDuringStreaming()`
**File:** `webapp/static/js/chat.js:384-406`

```javascript
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
            <div class="artifact-loading-header">
                <div class="artifact-loading-icon">📊</div>
                <div class="artifact-loading-text">Creating visualization...</div>
            </div>
            <div class="artifact-loading-bar">
                <div class="artifact-loading-progress"></div>
            </div>
        </div>\n\n`;
    });

    return textWithPlaceholders;
}
```

**Effect:**
- As AI streams: "Here's the trend ```artifact\n<!DOCTYPE html>..."
- User sees: "Here's the trend [LOADING ANIMATION]"
- Regex matches incomplete artifacts too: `(?:```|$)` means "closing ``` OR end of string"

### 8. Parsing Complete Artifacts
**Event:** `answer_end`
**File:** `webapp/static/js/chat.js:213-248`

```javascript
} else if (event.type === 'answer_end') {
    if (event.clean_answer) {
        fullAnswer = event.clean_answer;  // Complete answer from backend
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
}
```

**Function:** `parseArtifacts()`
**File:** `webapp/static/js/chat.js:408-432`

```javascript
parseArtifacts(text) {
    /**
     * Parse artifact blocks from AI response.
     * Artifacts are wrapped in ```artifact blocks.
     * Returns: { cleanAnswer: string, artifacts: array }
     */
    const artifacts = [];
    const artifactRegex = /```artifact\n([\s\S]*?)```/g;  // COMPLETE artifacts only

    let match;
    let cleanAnswer = text;

    // Extract all artifacts
    while ((match = artifactRegex.exec(text)) !== null) {
        artifacts.push({
            html: match[1].trim(),  // Extract HTML content
            id: 'artifact-' + Date.now() + '-' + artifacts.length
        });
    }

    // Remove artifact blocks from answer
    cleanAnswer = text.replace(artifactRegex, '').trim();

    return { cleanAnswer, artifacts };
}
```

### 9. Rendering Artifacts in Iframes
**Function:** `renderArtifact()`
**File:** `webapp/static/js/chat.js:434-475`

```javascript
renderArtifact(messageDiv, artifact) {
    /**
     * Render an HTML artifact in an isolated iframe with download capability.
     */
    const artifactContainer = document.createElement('div');
    artifactContainer.className = 'artifact-container';
    artifactContainer.id = artifact.id;

    // Create iframe for isolated rendering
    const iframe = document.createElement('iframe');
    iframe.className = 'artifact-iframe';
    iframe.sandbox = 'allow-scripts allow-same-origin';
    iframe.srcdoc = artifact.html;  // Inject complete HTML

    // Download button
    const downloadBtn = document.createElement('button');
    downloadBtn.className = 'artifact-download-btn';
    downloadBtn.innerHTML = `...Download HTML...`;
    downloadBtn.onclick = () => this.downloadArtifact(artifact);

    artifactContainer.appendChild(iframe);
    artifactContainer.appendChild(downloadBtn);
    messageDiv.appendChild(artifactContainer);

    // Auto-adjust iframe height after load
    iframe.addEventListener('load', () => {
        try {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            const height = iframeDoc.body.scrollHeight;
            iframe.style.height = Math.min(height + 20, 600) + 'px';
        } catch (e) {
            iframe.style.height = '500px';  // Fallback
        }
    });
}
```

### 10. CSS Animations
**File:** `webapp/static/css/chat.css:642-722`

**Loading Animation:**
```css
.artifact-loading {
    margin: 1.25rem 0;
    padding: 24px;
    border: 2px dashed var(--surface-border);
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(123, 171, 174, 0.05) 0%, rgba(83, 124, 138, 0.05) 100%);
    animation: artifactPulse 2s ease-in-out infinite;
}

@keyframes artifactPulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
}

@keyframes iconBounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-4px); }
}

@keyframes loadingProgress {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
```

**Artifact Fade-In:**
```css
.artifact-container {
    animation: artifactFadeIn 0.4s ease-out;
}

@keyframes artifactFadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

---

## 🐛 Debugging Checklist

### Issue: Raw HTML visible during streaming

**Check:**
1. Is `hideArtifactsDuringStreaming()` being called?
   - Set breakpoint at line 299 in chat.js
   - Verify `displayText` replaces artifact blocks

2. Is the regex matching?
   ```javascript
   const artifactRegex = /```artifact\n([\s\S]*?)(?:```|$)/g;
   ```
   - Test in console: `"```artifact\n<html>".match(artifactRegex)`

3. Is loading animation HTML valid?
   - Check for `<div class="artifact-loading">` in DOM during streaming

**Console Test:**
```javascript
const text = "Here is a chart ```artifact\n<!DOCTYPE html>\n<html>...</html>\n``` done";
const cleaned = text.replace(/```artifact\n([\s\S]*?)(?:```|$)/g, '[LOADING]');
console.log(cleaned);  // Should show: "Here is a chart [LOADING] done"
```

### Issue: Loading animation never disappears

**Check:**
1. Is `answer_end` event fired?
   - Add console.log in line 213: `console.log('answer_end received', event);`

2. Are artifacts parsed correctly?
   ```javascript
   const { cleanAnswer, artifacts } = this.parseArtifacts(fullAnswer);
   console.log('Parsed artifacts:', artifacts.length);
   ```

3. Is artifact block closed?
   - Search for closing ` ``` ` in fullAnswer
   - Regex requires BOTH opening and closing backticks for final parse

### Issue: Artifact doesn't render (blank iframe)

**Check:**
1. Is HTML complete?
   ```javascript
   console.log('Artifact HTML:', artifact.html);
   ```

2. Are there JavaScript errors in iframe?
   - Right-click iframe → Inspect Element
   - Check iframe console for errors

3. Is Chart.js loaded?
   - Open iframe console
   - Type: `typeof Chart`
   - Should return: "function"

4. Is srcdoc attribute set?
   ```javascript
   console.log('iframe.srcdoc:', iframe.srcdoc);
   ```

### Issue: AI plots Lat/Lon on charts

**Check system prompt (server/main.py:1452-1455):**
```python
3. **Column Selection**:
   - For Y-axis: Use count columns (Birds, Nests, total_birds, bird_count)
   - For X-axis: Use Year, Date, ColonyName, SpeciesName
   - **NEVER use Latitude/Longitude for chart axes!**
```

**Review generated artifact:**
- Look for `labels:` and `data:` in Chart.js config
- Verify no lat/lon values in arrays

---

## 🎯 Key Timing Points

1. **t=0s:** User submits question
2. **t=1-3s:** Agentic reasoning (analysis, SQL gen, validation)
3. **t=3s:** Query execution
4. **t=3.5s:** `answer_start` event → hide thinking indicator
5. **t=3.5-7s:** Answer streaming with `answer_chunk` events
   - **Artifact code replaced with loading animation on every chunk**
6. **t=7s:** `answer_end` event
   - **Parse complete artifacts**
   - **Remove loading animations**
   - **Render artifacts in iframes**
   - **Fade-in animation plays**
7. **t=7.5s:** Data table renders
8. **t=8s:** Map renders (if applicable)
9. **t=8s:** `done` event → re-enable input

---

## 📊 State Tracking

### During Streaming:
```javascript
// In sendMessage() function
let fullAnswer = '';      // Accumulates complete answer
let sqlQuery = '';        // SQL query from backend
let results = null;       // Query results array
let thinkingSteps = [];   // Reasoning steps

// Updated on each event
event.type === 'answer_chunk' → fullAnswer += event.content
event.type === 'sql_generated' → sqlQuery = event.content
event.type === 'results' → results = event.content
event.type === 'thinking_step' → thinkingSteps.push(event.content)
```

### After Streaming:
```javascript
// In answer_end handler
const { cleanAnswer, artifacts } = this.parseArtifacts(fullAnswer);

// cleanAnswer: Text without artifact blocks
// artifacts: [{html: '...', id: '...'}]
```

---

## ✅ Verification Commands

**Check if regex works:**
```javascript
const test = `Before ```artifact
<!DOCTYPE html>
<html></html>
``` After`;

// During streaming (incomplete closing)
const incomplete = test.slice(0, 30);  // "Before ```artifact\n<!DOCTYPE "
const cleaned = incomplete.replace(/```artifact\n([\s\S]*?)(?:```|$)/g, '[LOADING]');
console.log(cleaned);  // Should be: "Before [LOADING]"

// After streaming (complete)
const { cleanAnswer, artifacts } = parseArtifacts(test);
console.log(cleanAnswer);  // Should be: "Before  After"
console.log(artifacts.length);  // Should be: 1
```

---

**Created:** 2026-03-14
**Purpose:** Technical debugging reference for artifact rendering system
