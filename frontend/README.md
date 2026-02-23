# Frontend - Streamlit Web Interface

The frontend is the user-facing web application built with **Streamlit**, a Python framework for creating interactive data apps. Think of it as the "face" of NestScope that users interact with.

## What is Streamlit?

Streamlit is a Python library that makes it easy to create web apps without writing HTML, CSS, or JavaScript. You write Python code, and Streamlit automatically creates the web interface. It's like magic for data scientists who want to build apps quickly!

## How to Run

Start the frontend server:
```bash
streamlit run frontend/app.py --server.port 8501
```

Then open your browser to: **http://localhost:8501**

## Project Structure

```
frontend/
├── app.py                  # Main entry point - the landing page
├── pages/                  # Different pages of the app
│   ├── 01_nest_chat.py    # NestChat: Talk to your data
│   ├── 02_nest_vision.py  # NestVision: Upload images for bird detection
│   ├── 03_system_status.py # System health monitoring
│   └── 04_db_editor.py    # Database editor interface
├── components/             # Reusable UI pieces
│   ├── charts.py          # Chart rendering (line, bar, etc.)
│   ├── maps.py            # Geographic map displays
│   ├── sidebar.py         # Navigation sidebar
│   ├── top_bar.py         # Fixed top navigation bar
│   ├── loading.py         # Loading spinners and animations
│   └── status.py          # Status indicators
├── services/               # Backend communication
│   ├── api_client.py      # Talks to FastAPI backend
│   └── config.py          # Configuration management
├── utils/                  # Helper functions
│   ├── data_processing.py # Data transformation utilities
│   └── image_processing.py # Image handling utilities
└── styles/                 # Visual appearance
    └── theme.py           # Custom CSS and theming
```

## Key Concepts

### 1. Streamlit Pages
Streamlit automatically creates a multi-page app when you put Python files in a `pages/` folder. Each file becomes a page:
- `01_nest_chat.py` → "Nest Chat" page
- `02_nest_vision.py` → "Nest Vision" page

The numbers (01, 02) control the order they appear in the sidebar.

### 2. Session State
`st.session_state` is like the app's memory. It stores data between interactions:
```python
# Store a value
st.session_state.user_name = "Olise"

# Retrieve it later (even after button clicks)
print(st.session_state.user_name)  # "Olise"
```

**Important**: Session state is page-specific. If you switch pages, the state resets.

### 3. Components
Components are reusable UI elements. Instead of copying the same code everywhere, we create a component once and reuse it:
```python
from components.charts import render_line_chart

# Use the component anywhere
render_line_chart(data, title="Bird Observations Over Time")
```

## How Pages Work

### NestChat (01_nest_chat.py)
This page lets users ask questions about bird data in natural language.

**Flow:**
1. User types: "What colonies had the most Brown Pelicans in 2015?"
2. Frontend sends question to backend API
3. Backend generates SQL, runs it, creates an answer
4. Frontend displays answer, chart, and/or map

**Key features:**
- Streaming responses (words appear one by one)
- Automatic visualization based on LLM directives
- Export results to CSV
- Conversation history

### NestVision (02_nest_vision.py)
This page lets users upload bird images for AI detection and counting.

**Flow:**
1. User uploads an image or selects an example
2. User adjusts confidence threshold slider
3. User chooses Fast or SAHI mode
4. Frontend sends image to backend `/cv/inference` endpoint
5. Backend returns annotated image with bounding boxes
6. Frontend displays results and bird count

**Key features:**
- Image upload or example selection
- Confidence threshold adjustment
- Mode switching (Fast vs SAHI)
- "Train with Experts" button (sends to Nestperts)

## API Communication

The `services/api_client.py` file handles all communication with the FastAPI backend:

```python
# Example: Ask a question
response = ask_question_stream(
    question="How many colonies are in Texas?",
    model="anthropic/claude-sonnet-4.5"
)

# Example: Run inference
result = run_inference(
    image_file=uploaded_file,
    conf_threshold=0.25,
    fast_mode=True
)
```

### Why separate API client?
- **Organization**: All API calls in one place
- **Reusability**: Multiple pages can use the same functions
- **Maintainability**: If the API changes, update one file

## Styling and Theming

The `styles/theme.py` file contains custom CSS that makes NestScope look unique:
- Dark theme with orange accents (Claude orange: #D97757)
- Custom button styles
- Fixed navigation bars
- Responsive layouts

CSS is injected using:
```python
st.markdown(css_string, unsafe_allow_html=True)
```

## Common Streamlit Patterns

### 1. Columns (Side-by-Side Layout)
```python
col1, col2 = st.columns(2)
with col1:
    st.write("Left side")
with col2:
    st.write("Right side")
```

### 2. File Uploader
```python
uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png"])
if uploaded_file:
    # Process the file
    image = Image.open(uploaded_file)
```

### 3. Buttons and Callbacks
```python
if st.button("Click me"):
    st.success("Button clicked!")
```

### 4. Displaying Images
```python
st.image(image, caption="Bird Photo", use_column_width=True)
```

## Debugging Tips

### View Logs
Streamlit prints errors and logs to the terminal where you ran the command.

### Clear Cache
If the app behaves strangely, clear Streamlit's cache:
- Press `C` in the terminal running Streamlit
- Or add `?clear_cache=true` to the URL

### Session State Inspection
Add this to any page to see what's in session state:
```python
st.write("Session State:", st.session_state)
```

## Development Workflow

1. **Make changes** to Python files
2. **Save the file**
3. Streamlit **auto-detects changes** and shows "Rerun" button
4. Click **"Always rerun"** for automatic refresh

## Environment Variables

The frontend reads configuration from `.env`:
- `API_BASE_URL`: Backend API URL (default: http://localhost:8000)
- `MODEL_NAME`: LLM model to use (default: anthropic/claude-sonnet-4.5)

## Dependencies

Key Python packages used:
- `streamlit`: Web framework
- `requests`: HTTP communication with backend
- `plotly`: Interactive charts
- `folium`: Map visualizations
- `pandas`: Data manipulation
- `PIL`: Image processing

Install all dependencies:
```bash
pip install -r requirements.txt
```

## Common Issues

### "Connection Refused" Error
**Problem**: Frontend can't reach backend
**Solution**: Make sure backend is running on port 8000:
```bash
python -m uvicorn server.main:app --port 8000
```

### Page Not Updating
**Problem**: Changes don't appear
**Solution**:
- Check if Streamlit detected the change
- Click "Rerun" or "Always rerun"
- Clear cache with `C` in terminal

### Import Errors
**Problem**: `ModuleNotFoundError: No module named 'xyz'`
**Solution**:
```bash
# Activate virtual environment first
source .venv/bin/activate
# Then install
pip install -r requirements.txt
```

## Learning Resources

- **Streamlit Docs**: https://docs.streamlit.io
- **Streamlit Gallery**: https://streamlit.io/gallery (see examples)
- **Plotly Charts**: https://plotly.com/python/
- **Folium Maps**: https://python-visualization.github.io/folium/

## Next Steps

To understand the frontend better:
1. Read `app.py` - the main entry point
2. Look at `pages/01_nest_chat.py` - simplest page
3. Check `services/api_client.py` - how we talk to backend
4. Explore `components/` - reusable UI elements
