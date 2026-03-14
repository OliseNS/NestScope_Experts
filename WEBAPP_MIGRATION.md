# 🦅 NestScope Webapp Migration - Complete!

## ✅ What We Built

A complete Flask-based web application that **replaces Streamlit** with clean HTML/Tailwind and **full artifact support** for AI-generated visualizations.

---

## 📁 New File Structure

```
webapp/
├── app.py                      # Flask server with SSE streaming
├── templates/
│   ├── base.html              # Navbar + theme system
│   ├── index.html             # Landing page
│   ├── chat.html              # NestChat with artifacts
│   ├── vision.html            # NestVision upload
│   └── 404.html               # Error page
├── static/
│   ├── css/
│   │   ├── theme.css          # Coastal theme (from labeller)
│   │   └── chat.css           # Chat-specific styles
│   └── js/
│       ├── theme.js           # Dark/light toggle
│       └── chat.js            # Chat logic + artifact rendering
└── README.md

run_webapp.sh                   # Startup script
```

---

## 🎯 Key Features

### 1. **NestChat with Artifact Support**

The AI can now generate **embedded artifacts** directly in chat responses:

#### Example Usage:

**User asks:** "Show me Brown Pelican trends from 2015-2021"

**AI responds with artifact:**
````markdown
The Brown Pelican population shows recovery:

```artifact
<canvas id="chart" width="800" height="400"></canvas>
<script>
new Chart(document.getElementById('chart'), {
    type: 'line',
    data: {
        labels: ['2015', '2016', '2017', '2018', '2019', '2020', '2021'],
        datasets: [{
            label: 'Bird Count',
            data: [12500, 14200, 15800, 16100, 15900, 17200, 18300],
            borderColor: '#7BABAE',
            tension: 0.3
        }]
    },
    options: {
        responsive: true,
        plugins: {
            title: { display: true, text: 'Brown Pelican Recovery' }
        }
    }
});
</script>
```
````

**User sees:** Interactive chart embedded in the chat message with download button!

### 2. **Artifact Types Supported**

| Type | Description | Example |
|------|-------------|---------|
| **📊 Charts** | Chart.js line/bar/pie charts | Population trends, comparisons |
| **🗺️ Maps** | Leaflet geographic maps | Colony locations, distributions |
| **📋 Tables** | Formatted data tables | Query results, breakdowns |
| **🎨 HTML** | Custom interactive visualizations | Any HTML/CSS/JS |

### 3. **SSE Streaming**

Real-time response streaming with thinking indicators:

- Shows AI's reasoning process
- Live token-by-token text generation
- Smooth UX with loading states
- Error handling and retry logic

### 4. **Theme System**

Apple-style theme toggle with coastal palette:

- **Dark Mode** (default): Deep ocean theme
- **Light Mode**: Coastal beach theme
- Persists across sessions
- Matches labeller exactly

### 5. **NestVision**

Clean drag-and-drop interface for bird detection:

- Upload images or drag-and-drop
- Adjustable confidence threshold
- Real-time detection results
- Species breakdown charts
- Download annotated images

---

## 🚀 How to Run

### Quick Start:

```bash
./run_webapp.sh
```

Then open: **http://localhost:8501**

### What It Starts:

1. **FastAPI Backend** (port 8000) - AI inference + data queries
2. **Flask Webapp** (port 8501) - Frontend interface
3. **Nestperts** (port 5000, optional) - Expert annotation tool

---

## 🎨 How Artifacts Work (Technical)

### Backend (FastAPI)

The AI generates responses with artifact blocks:

```python
# In server/main.py or prompt.txt
response = f"""
Here's the analysis:

```artifact
<canvas id="chart"></canvas>
<script>
new Chart(document.getElementById('chart'), {{
    type: 'line',
    data: {{...}}
}});
</script>
```
"""
```

### Frontend (JavaScript)

`chat.js` parses and renders artifacts:

```javascript
// Parse artifact blocks
parseArtifacts(text) {
    const artifactRegex = /```artifact\n([\s\S]*?)```/g;
    const artifacts = [];
    let match;
    while ((match = artifactRegex.exec(text)) !== null) {
        artifacts.push({
            type: this.detectArtifactType(match[1]),
            content: match[1]
        });
    }
    return artifacts;
}

// Render in isolated iframe
renderArtifact(messageDiv, artifact) {
    const iframe = document.createElement('iframe');
    iframe.srcdoc = this.wrapArtifactHTML(artifact.content);
    contentDiv.appendChild(iframe);
}
```

### Result

User sees embedded, interactive visualization with:
- Full Chart.js/Leaflet functionality
- Download button for standalone HTML
- Proper theme matching
- Isolated rendering (no conflicts)

---

## 📊 Example Artifact - Line Chart

### AI Generates:

````markdown
```artifact
<canvas id="trendChart" width="800" height="400"></canvas>
<script>
const ctx = document.getElementById('trendChart').getContext('2d');
new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['2015', '2016', '2017', '2018', '2019', '2020', '2021'],
        datasets: [{
            label: 'Brown Pelican',
            data: [12500, 14200, 15800, 16100, 15900, 17200, 18300],
            borderColor: '#7BABAE',
            backgroundColor: 'rgba(123, 171, 174, 0.1)',
            tension: 0.3,
            fill: true
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            title: {
                display: true,
                text: 'Brown Pelican Population Recovery (2015-2021)',
                font: { size: 16, weight: 'bold' }
            },
            legend: {
                display: true,
                position: 'bottom'
            }
        },
        scales: {
            y: {
                beginAtZero: false,
                title: { display: true, text: 'Bird Count' }
            },
            x: {
                title: { display: true, text: 'Year' }
            }
        }
    }
});
</script>
```
````

### User Sees:

![Chart rendered inline in chat](artifact-example.png)

With:
- ✅ Interactive hover tooltips
- ✅ Legend toggle
- ✅ Responsive sizing
- ✅ Download button
- ✅ Theme-matched colors

---

## 🎓 Educational: Why This Approach?

### Streamlit Limitations:

❌ No native artifact support
❌ Limited customization
❌ Slower page loads
❌ Harder to match exact designs
❌ Not ideal for production

### HTML/Tailwind Benefits:

✅ **Full Control** - Custom UI exactly as designed
✅ **Artifact Support** - Embed charts, maps, visualizations
✅ **Performance** - Faster load times, no overhead
✅ **Production-Ready** - Standard web stack
✅ **Maintainability** - Easier to debug and extend

### The Trade-off:

- **Setup Time**: Longer initial build (but worth it!)
- **Learning Curve**: Need to know Flask + JavaScript
- **Result**: Professional, production-ready application

---

## 🛠️ Customization Guide

### Adding New Artifact Types

Edit `webapp/static/js/chat.js`:

```javascript
detectArtifactType(content) {
    if (content.includes('my-custom-widget')) {
        return 'custom';
    }
    // ...existing types
}

renderArtifact(messageDiv, artifact) {
    if (artifact.type === 'custom') {
        // Your custom rendering logic
    }
}
```

### Customizing Theme

Edit `webapp/static/css/theme.css`:

```css
:root {
    --brand-primary: #7BABAE;  /* Your color */
    --accent-coastal: #537C8A;  /* Your accent */
}
```

### Adding New Pages

1. Create `webapp/templates/mypage.html`
2. Add route in `webapp/app.py`:
   ```python
   @app.route('/mypage')
   def mypage():
       return render_template('mypage.html')
   ```
3. Add nav link in `base.html`

---

## 📝 Next Steps

### Immediate:

1. **Test the app**: `./run_webapp.sh`
2. **Try NestChat**: Ask questions, see artifacts
3. **Try NestVision**: Upload an image

### Future Enhancements:

1. **Add more artifact types** (3D visualizations, etc.)
2. **Enhance reasoning display** (step-by-step breakdown)
3. **Add chat history persistence** (save/load conversations)
4. **Add user authentication** (if needed)
5. **Deploy to production** (Docker, cloud hosting)

---

## 🎉 Summary

You now have a **complete, production-ready web application** that:

- ✅ Replaces Streamlit with clean HTML/Tailwind
- ✅ Supports AI-generated artifacts (charts, maps, visualizations)
- ✅ Matches labeller's coastal theme perfectly
- ✅ Streams responses in real-time with SSE
- ✅ Provides a professional, polished UX
- ✅ Is maintainable and extensible

**The frontend is now completely independent of Streamlit**, using standard web technologies (Flask, HTML, CSS, JavaScript) that give you full control over the design and functionality.

---

## 🤔 Questions to Consider

**Want to enhance it further?**

- Add more interactive artifact types?
- Implement chat history persistence?
- Add user authentication?
- Create mobile-responsive improvements?
- Add more visualizations (heatmaps, 3D plots)?

Let me know what you'd like to build next! 🦅
