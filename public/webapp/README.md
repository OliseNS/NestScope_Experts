# NestScope Web Application

Clean HTML/Tailwind frontend with Flask backend, replacing the Streamlit app.

## Architecture

```
webapp/
├── app.py                  # Flask server with SSE streaming
├── templates/
│   ├── base.html          # Base template with navbar + theme
│   ├── index.html         # Landing page
│   ├── chat.html          # NestChat interface
│   └── vision.html        # NestVision interface
├── static/
│   ├── css/
│   │   ├── theme.css      # Coastal theme (from labeller)
│   │   └── chat.css       # Chat-specific styles
│   └── js/
│       ├── theme.js       # Theme toggle (from labeller)
│       └── chat.js        # Chat logic with artifact support
└── README.md
```

## Key Features

### NestChat with Artifacts

The chat interface supports **AI-generated artifacts** that are embedded directly in responses:

- **Charts**: Interactive Chart.js visualizations
- **Maps**: Leaflet maps with colony locations
- **Tables**: Formatted data tables
- **HTML**: Custom interactive visualizations

#### How Artifacts Work

1. **Backend**: AI generates response with artifact blocks:
   ````markdown
   Here's the trend analysis:

   ```artifact
   <canvas id="chart"></canvas>
   <script>
   new Chart(document.getElementById('chart'), {
       type: 'line',
       data: { ... }
   });
   </script>
   ```
   ````

2. **Frontend**: `chat.js` parses artifact blocks and renders them in isolated iframes

3. **User**: Sees embedded chart directly in the chat message, can download it

### SSE Streaming

Chat responses stream in real-time using Server-Sent Events (SSE):

```javascript
const eventSource = new EventSource('/api/chat/stream?question=...');
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle: thinking_step, answer_chunk, answer_end, etc.
};
```

### Theme System

Supports dark/light modes with coastal color palette:

- **Dark Mode** (default): Deep ocean theme
- **Light Mode**: Coastal beach theme
- **Toggle**: Apple-style switch in navbar
- **Persistence**: Saves preference to localStorage

## Running the App

### Quick Start

```bash
./run_webapp.sh
```

This starts:
- FastAPI backend (port 8000)
- Flask webapp (port 8501)
- Nestperts (port 5000, optional)

### Manual Start

```bash
# Backend
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

# Webapp
cd webapp && python app.py

# Access
open http://localhost:8501
```

## API Endpoints

### Chat
- `GET /chat` - Chat interface
- `GET /api/chat/stream?question=...` - SSE streaming endpoint

### Vision
- `GET /vision` - Vision interface
- `POST /api/vision/inference` - Upload image for detection
- `GET /api/vision/examples` - List example images
- `GET /api/vision/example/<filename>` - Get example image

### Pages
- `GET /` - Landing page
- `GET /chat` - NestChat
- `GET /vision` - NestVision

## Development

### Adding New Pages

1. Create template in `templates/`
2. Add route in `app.py`
3. Add nav link in `base.html`
4. Create page-specific CSS if needed

### Customizing Artifacts

Edit `chat.js`:

```javascript
// Add new artifact type
detectArtifactType(content) {
    if (content.includes('my-custom-viz')) {
        return 'custom';
    }
    // ...
}

// Add rendering logic
renderArtifact(messageDiv, artifact) {
    if (artifact.type === 'custom') {
        // Custom rendering
    }
}
```

### Styling

- **Global**: Edit `static/css/theme.css` (shared with labeller)
- **Page-specific**: Create new CSS file and link in template
- **Colors**: Use CSS variables from theme.css

## Comparison: Streamlit vs HTML/Tailwind

| Feature | Streamlit | HTML/Tailwind |
|---------|-----------|---------------|
| Setup Time | ✅ Fast | ⚠️ Moderate |
| Customization | ❌ Limited | ✅ Full Control |
| Performance | ⚠️ Slower | ✅ Fast |
| Artifacts | ❌ No Native Support | ✅ Full Support |
| Production | ⚠️ Not Ideal | ✅ Ready |
| Theme Toggle | ❌ Complex | ✅ Simple |

## Technologies

- **Backend**: Flask (SSE streaming, API proxy)
- **Frontend**: HTML5, CSS3 (no framework)
- **Charts**: Chart.js 4.4.1
- **Maps**: Leaflet 1.9.4
- **Theme**: Custom CSS with CSS variables
- **Fonts**: DM Sans, JetBrains Mono

## Notes

- Port 8501 kept for compatibility with existing scripts
- SSE streaming requires backend on port 8000
- Artifacts render in iframes for security/isolation
- Theme matches labeller exactly (coastal palette)
- All API calls proxy through Flask to FastAPI backend
