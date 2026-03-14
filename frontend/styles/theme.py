"""
NestScope UI Styles
Glassmorphism dark theme with frosted glass panels
"""

def get_custom_css():
    """
    Returns the custom CSS styling for the NestScope application.
    Glassmorphism: backdrop-filter blur + semi-transparent surfaces + luminous borders.
    """
    return """
<style>
    /* Glassmorphism Dark Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    :root {
        --claude-orange: #D97757;
        --claude-orange-hover: #E5865F;
        --claude-orange-glow: rgba(217, 119, 87, 0.35);

        /* Glass surfaces */
        --glass-bg: rgba(255, 255, 255, 0.04);
        --glass-bg-hover: rgba(255, 255, 255, 0.08);
        --glass-border: rgba(255, 255, 255, 0.1);
        --glass-border-hover: rgba(255, 255, 255, 0.18);
        --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.06);
        --glass-shadow-hover: 0 12px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);

        /* Background */
        --bg-base: #0D0D12;
        --bg-gradient: radial-gradient(ellipse 80% 60% at 10% 0%, rgba(217, 119, 87, 0.12) 0%, transparent 50%),
                        radial-gradient(ellipse 60% 50% at 90% 80%, rgba(100, 160, 255, 0.08) 0%, transparent 50%),
                        radial-gradient(ellipse 70% 80% at 50% 50%, rgba(13, 13, 18, 1) 0%, #0D0D12 100%);

        --claude-text: #E8E8F0;
        --claude-text-light: #8888A0;
        --claude-orange-accent: rgba(217, 119, 87, 0.15);
    }

    /* Global Styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hide Streamlit Elements */
    #MainMenu, footer {visibility: hidden;}
    header {visibility: visible !important;}
    .stDeployButton {display: none;}

    /* Body Background — the "scene" behind the glass */
    .stApp {
        background: var(--bg-gradient) !important;
        background-color: var(--bg-base) !important;
        background-attachment: fixed !important;
    }

    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > section:first-child,
    .main {
        background: transparent !important;
    }

    /* Ensure Streamlit toolbar stays on top */
    [data-testid="stToolbar"],
    [data-testid="stHeader"],
    header {
        z-index: 999999 !important;
    }

    /* Main Container */
    .main .block-container {
        padding: 2rem 3rem 6rem;
        max-width: 1000px;
        margin: 0 auto;
        background: transparent !important;
    }

    /* ── Typography ── */
    h1 { color: var(--claude-text); font-weight: 600; font-size: 2.25rem; letter-spacing: -0.03em; margin-bottom: 0.5rem; line-height: 1.2; }
    h2 { color: var(--claude-text); font-weight: 600; font-size: 1.5rem; letter-spacing: -0.02em; margin-top: 2rem; margin-bottom: 1rem; line-height: 1.3; }
    h3 { color: var(--claude-text); font-weight: 600; font-size: 1.125rem; letter-spacing: -0.015em; margin-top: 1.5rem; margin-bottom: 0.75rem; line-height: 1.4; }
    h4 { color: var(--claude-text); font-weight: 600; font-size: 1rem; letter-spacing: -0.01em; line-height: 1.5; }

    .main .block-container > div:first-child p {
        color: var(--claude-text-light);
        font-size: 0.9375rem;
        margin-top: 0;
        line-height: 1.6;
    }

    ul, ol { color: var(--claude-text); line-height: 1.8; }
    li { margin: 0.375rem 0; }

    a { color: var(--claude-orange); text-decoration: none; transition: color 0.2s ease; }
    a:hover { color: var(--claude-orange-hover); text-decoration: underline; }

    /* ── Glass Card Base ── */
    .glass-panel {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 16px;
        box-shadow: var(--glass-shadow);
    }

    /* ── Title Card ── */
    .title-card {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 14px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: var(--glass-shadow);
    }

    .title-card h3 {
        color: var(--claude-text);
        font-weight: 600;
        font-size: 1.25rem;
        margin: 0 0 1rem 0;
        line-height: 1.4;
    }

    .title-card p {
        color: var(--claude-text-light);
        line-height: 1.7;
        margin: 0;
        font-size: 0.9375rem;
    }

    /* ── Feature Cards ── */
    .feature-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 16px;
        padding: 1.75rem;
        height: 100%;
        transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.06);
    }

    .feature-card:hover {
        border-color: rgba(217, 119, 87, 0.4);
        background: rgba(255, 255, 255, 0.07);
        transform: translateY(-3px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(217, 119, 87, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }

    /* ── Chat Messages ── */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        padding: 1.5rem 0 !important;
        margin: 0 !important;
        animation: fadeIn 0.3s ease-out;
    }

    .stChatMessage > div { padding: 0 !important; }

    [data-testid="stChatMessageContent"] {
        background: transparent !important;
        padding: 0 !important;
        color: var(--claude-text) !important;
        font-size: 0.9375rem !important;
        line-height: 1.7 !important;
    }

    /* ── Chat Input — Glass floating bar ── */
    .stChatInput {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 1rem 0 1.5rem;
        background: linear-gradient(to top, rgba(13,13,18,0.95) 0%, rgba(13,13,18,0.6) 80%, transparent 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-top: none !important;
        z-index: 100;
    }

    .stChatInput > div {
        max-width: 1200px !important;
        width: 100% !important;
        margin: 0 auto !important;
        padding: 0 3rem !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    .stChatInput > div > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    .stChatInput textarea {
        width: 100% !important;
        min-height: 52px !important;
        max-height: 200px !important;
        background: rgba(255, 255, 255, 0.06) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 14px !important;
        font-size: 15px !important;
        padding: 14px 50px 14px 16px !important;
        color: var(--claude-text) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
        resize: none !important;
        line-height: 24px !important;
        font-family: Inter, sans-serif !important;
        font-weight: 400 !important;
    }

    .stChatInput textarea:focus {
        border-color: rgba(217, 119, 87, 0.6) !important;
        border-width: 1px !important;
        box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.12), 0 4px 24px rgba(0, 0, 0, 0.3) !important;
        outline: none !important;
    }

    .stChatInput textarea:hover:not(:focus) {
        border-color: rgba(255, 255, 255, 0.2) !important;
    }

    .stChatInput textarea::placeholder {
        color: var(--claude-text-light) !important;
        opacity: 0.6;
        font-size: 15px !important;
        font-weight: 400 !important;
    }

    .stChatInput button[kind="primary"] {
        background: var(--claude-orange) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 12px rgba(217, 119, 87, 0.35) !important;
    }

    .stChatInput button[kind="primary"]:hover {
        background: var(--claude-orange-hover) !important;
        box-shadow: 0 4px 16px rgba(217, 119, 87, 0.5) !important;
    }

    /* ── Sidebar — Glass panel ── */
    [data-testid="stSidebar"] {
        background: rgba(13, 13, 18, 0.7) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        padding: 0;
        z-index: 999998 !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 0 0.75rem;
        background: transparent !important;
    }

    [data-testid="stSidebar"] h3 {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--claude-text);
        margin-bottom: 0.25rem;
        padding: 0 0.5rem;
    }

    [data-testid="stSidebar"] .caption {
        color: var(--claude-text-light);
        font-size: 0.75rem;
        padding: 0 0.5rem;
        margin-bottom: 1rem;
    }

    [data-testid="stSidebar"] h4 {
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--claude-text-light);
        margin: 1.75rem 0 0.5rem;
        padding: 0 0.5rem;
        opacity: 0.7;
    }

    [data-testid="stSidebar"] hr {
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        margin: 1.5rem 0;
        opacity: 0.5;
    }

    /* Sidebar Buttons — glass pill style */
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border: 1px solid transparent;
        background: transparent;
        color: var(--claude-text);
        border-radius: 10px;
        padding: 0.625rem 0.75rem;
        font-weight: 500;
        font-size: 0.8125rem;
        transition: all 0.18s ease;
        text-align: left;
        margin: 2px 0;
        position: relative;
        line-height: 1.5;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(217, 119, 87, 0.1);
        border-color: rgba(217, 119, 87, 0.2);
        color: var(--claude-orange);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }

    [data-testid="stSidebar"] .stButton > button:active {
        background: rgba(217, 119, 87, 0.18);
    }

    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: rgba(217, 119, 87, 0.12) !important;
        color: var(--claude-orange) !important;
        border: 1px solid rgba(217, 119, 87, 0.25) !important;
        font-weight: 600 !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.06) !important;
    }

    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: rgba(217, 119, 87, 0.2) !important;
        border-color: rgba(217, 119, 87, 0.45) !important;
        box-shadow: 0 0 12px rgba(217, 119, 87, 0.15), inset 0 1px 0 rgba(255,255,255,0.08) !important;
    }

    [data-testid="stSidebar"] .element-container { margin-bottom: 0.125rem; }
    [data-testid="stSidebar"] .stMarkdown { margin-bottom: 0; }

    [data-testid="stSidebar"] ::-webkit-scrollbar { width: 6px; }
    [data-testid="stSidebar"] ::-webkit-scrollbar-track { background: transparent; }
    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.08); border-radius: 3px; }
    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.14); }

    /* ── Main content buttons ── */
    .main .stButton > button {
        width: 100%;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        color: var(--claude-text);
        border-radius: 12px;
        padding: 0.75rem 1rem;
        font-weight: 500;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        text-align: left;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
    }

    .main .stButton > button:hover {
        background: rgba(255, 255, 255, 0.09);
        border-color: rgba(217, 119, 87, 0.4);
        color: var(--claude-orange);
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        color: var(--claude-text) !important;
        padding: 0.875rem 1rem !important;
        transition: all 0.2s ease !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: rgba(217, 119, 87, 0.35) !important;
        background: rgba(255, 255, 255, 0.07) !important;
    }

    .streamlit-expanderContent {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
        padding: 1rem !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 0;
        padding: 0.875rem 1.25rem;
        border: none;
        border-bottom: 2px solid transparent;
        font-weight: 500;
        font-size: 0.9375rem;
        color: var(--claude-text-light);
        background: transparent;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover { color: var(--claude-text); background: transparent; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { border-bottom-color: var(--claude-orange); color: var(--claude-orange); }

    /* ── Alerts ── */
    .stAlert {
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        font-size: 0.875rem;
        color: var(--claude-text);
        padding: 0.875rem 1rem;
    }

    /* ── Dataframes ── */
    .stDataFrame {
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        overflow: hidden;
        font-size: 0.875rem;
        backdrop-filter: blur(12px);
    }

    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: rgba(255, 255, 255, 0.03);
    }

    /* ── Download Button ── */
    .stDownloadButton > button {
        background: var(--claude-orange) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 12px rgba(217, 119, 87, 0.35) !important;
    }

    .stDownloadButton > button:hover {
        background: var(--claude-orange-hover) !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(217, 119, 87, 0.45) !important;
    }

    /* ── Metrics — Glass cards ── */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 14px;
        padding: 1.25rem;
        transition: all 0.25s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.06);
    }

    [data-testid="stMetric"]:hover {
        border-color: rgba(217, 119, 87, 0.3);
        transform: translateY(-2px);
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(217, 119, 87, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }

    [data-testid="stMetricValue"] { font-size: 1.75rem; font-weight: 600; color: var(--claude-orange); }

    [data-testid="stMetricLabel"] {
        font-size: 0.75rem;
        color: var(--claude-text-light);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    /* ── Loading Spinner ── */
    .stSpinner > div { border-top-color: var(--claude-orange) !important; }

    /* ── Sidebar info boxes ── */
    [data-testid="stSidebar"] .stAlert {
        background: rgba(217, 119, 87, 0.06);
        border-left: 3px solid var(--claude-orange);
        border-radius: 8px;
        font-size: 0.8125rem;
    }

    /* ── Code blocks ── */
    code {
        background: rgba(255, 255, 255, 0.08) !important;
        color: var(--claude-orange) !important;
        padding: 0.2em 0.4em !important;
        border-radius: 5px !important;
        font-size: 0.875em !important;
    }

    pre {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        backdrop-filter: blur(12px) !important;
    }

    pre code { background: transparent !important; color: var(--claude-text) !important; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.16); }

    .stMarkdown strong { color: var(--claude-orange); }

    /* ── Animations ── */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .stChatMessage { animation: fadeIn 0.3s ease-out; }

    /* ── File Uploader ── */
    [data-testid="stFileUploader"] {
        border: 2px dashed rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        padding: 1.5rem;
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(12px);
        transition: all 0.2s ease;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: rgba(217, 119, 87, 0.4);
        background: rgba(255, 255, 255, 0.06);
    }

    /* ── Slider ── */
    .stSlider { padding: 1rem 0; }

    /* ── Radio buttons ── */
    .stRadio > div { gap: 0.75rem; }

    /* ── Columns ── */
    [data-testid="column"] { padding: 0 0.75rem; }
    [data-testid="column"]:first-child { padding-left: 0; }
    [data-testid="column"]:last-child { padding-right: 0; }

    /* ── Sidebar collapse button ── */
    [data-testid="collapsedControl"] {
        background: rgba(255, 255, 255, 0.06) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.2s ease !important;
        z-index: 999999 !important;
    }

    [data-testid="collapsedControl"]:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(217, 119, 87, 0.4) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
        transform: scale(1.05) !important;
    }

    [data-testid="collapsedControl"] svg { stroke: var(--claude-text) !important; }
    [data-testid="collapsedControl"]:hover svg { stroke: var(--claude-orange) !important; }

    /* ── Form elements ── */
    .stTextInput, .stNumberInput, .stSelectbox { margin-bottom: 1rem; }

    img { border-radius: 8px; }

    .js-plotly-plot { border-radius: 12px; overflow: hidden; }

    /* ── Select boxes ── */
    [data-testid="stSelectbox"] > div > div {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        transition: border-color 0.2s ease !important;
    }

    [data-testid="stSelectbox"] > div > div:hover { border-color: rgba(255, 255, 255, 0.18) !important; }

    [data-testid="stSelectbox"] > div > div:focus-within {
        border-color: rgba(217, 119, 87, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.1) !important;
    }

    /* ── Text inputs ── */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: var(--claude-text) !important;
        transition: border-color 0.2s ease !important;
        padding: 0.5rem 0.75rem !important;
    }

    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: rgba(217, 119, 87, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.1) !important;
    }

    /* ── Textarea ── */
    [data-testid="stTextArea"] textarea {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: var(--claude-text) !important;
        transition: border-color 0.2s ease !important;
    }

    [data-testid="stTextArea"] textarea:focus {
        border-color: rgba(217, 119, 87, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(217, 119, 87, 0.1) !important;
    }

    /* ── Primary buttons in main content ── */
    .main .stButton > button[kind="primary"] {
        background: var(--claude-orange) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 12px rgba(217, 119, 87, 0.35) !important;
    }

    .main .stButton > button[kind="primary"]:hover {
        background: var(--claude-orange-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(217, 119, 87, 0.45) !important;
    }

    /* ── Link buttons ── */
    .main .stLinkButton > a {
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(12px) !important;
        color: var(--claude-text) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        transition: all 0.2s ease !important;
    }

    .main .stLinkButton > a:hover {
        background: rgba(255, 255, 255, 0.09) !important;
        border-color: rgba(217, 119, 87, 0.4) !important;
        color: var(--claude-orange) !important;
        transform: translateY(-1px) !important;
        text-decoration: none !important;
    }

    /* ── Progress bar ── */
    .stProgress > div > div > div {
        background-color: var(--claude-orange) !important;
        border-radius: 4px !important;
        box-shadow: 0 0 8px rgba(217, 119, 87, 0.4) !important;
    }

    /* ── Multiselect tags ── */
    [data-baseweb="tag"] {
        background: rgba(217, 119, 87, 0.12) !important;
        color: var(--claude-orange) !important;
        border-radius: 5px !important;
        border: 1px solid rgba(217, 119, 87, 0.25) !important;
        backdrop-filter: blur(8px) !important;
    }

    /* ── Radio buttons ── */
    [data-testid="stRadio"] > div { gap: 0.625rem !important; }

    [data-testid="stRadio"] label {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 10px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }

    [data-testid="stRadio"] label:hover {
        border-color: rgba(255, 255, 255, 0.16) !important;
        background: rgba(255, 255, 255, 0.07) !important;
    }

    /* ── Checkbox ── */
    [data-testid="stCheckbox"] label { gap: 0.5rem !important; }

    /* ── Dividers ── */
    .main hr {
        border: none !important;
        border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
        margin: 1.5rem 0 !important;
        opacity: 1 !important;
    }

    /* ── Toast notifications ── */
    [data-testid="stToast"] {
        background: rgba(30, 30, 40, 0.85) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: var(--claude-text) !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
    }

    /* ── Caption / small text ── */
    [data-testid="stCaptionContainer"] p {
        color: var(--claude-text-light) !important;
        font-size: 0.8125rem !important;
    }

    /* ── Alert states ── */
    .stSuccess { border-color: rgba(52, 199, 89, 0.3) !important; background: rgba(52, 199, 89, 0.06) !important; }
    .stError { border-color: rgba(255, 69, 58, 0.3) !important; background: rgba(255, 69, 58, 0.06) !important; }
    .stWarning { border-color: rgba(255, 159, 10, 0.3) !important; background: rgba(255, 159, 10, 0.06) !important; }
    .stInfo { border-color: rgba(10, 132, 255, 0.3) !important; background: rgba(10, 132, 255, 0.06) !important; }

    /* ── Metric delta ── */
    [data-testid="stMetricDelta"] { font-size: 0.8125rem !important; }

    /* ── Table header ── */
    [data-testid="stDataFrame"] th {
        background: rgba(255, 255, 255, 0.06) !important;
        color: var(--claude-text-light) !important;
        font-weight: 600 !important;
        font-size: 0.8125rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }
</style>
"""
