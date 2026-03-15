"""
NestScope UI Styles
Clean, modern interface inspired by Claude Code
"""

def get_custom_css():
    """
    Returns the custom CSS styling for the NestScope application.
    """
    return """
<style>
    /* Claude Dark Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    :root {
        --claude-orange: #D97757;
        --claude-orange-hover: #E5865F;
        --claude-bg: #1A1A1A;
        --claude-surface: #2D2D2D;
        --claude-surface-hover: #3A3A3A;
        --claude-text: #E5E5E5;
        --claude-text-light: #A0A0A0;
        --claude-border: #404040;
        --claude-border-light: #4A4A4A;
        --claude-accent: #D97757;
    }

    /* Global Styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hide Streamlit Elements */
    #MainMenu, footer {visibility: hidden;}
    header {visibility: visible !important;}
    .stDeployButton {display: none;}

    /* Body Background */
    .stApp {
        background-color: var(--claude-bg);
    }

    /* Ensure Streamlit toolbar and controls stay on top */
    [data-testid="stToolbar"] {
        z-index: 999999 !important;
    }

    [data-testid="stHeader"] {
        z-index: 999999 !important;
    }

    header {
        z-index: 999999 !important;
    }

    /* Main Container - Improved spacing and max-width */
    .main .block-container {
        padding: 2rem 3rem 6rem;
        max-width: 1000px;
        margin: 0 auto;
    }

    /* Typography - Improved hierarchy */
    h1 {
        color: var(--claude-text);
        font-weight: 600;
        font-size: 2.25rem;
        letter-spacing: -0.03em;
        margin-bottom: 0.5rem;
        line-height: 1.2;
    }

    h2 {
        color: var(--claude-text);
        font-weight: 600;
        font-size: 1.5rem;
        letter-spacing: -0.02em;
        margin-top: 2rem;
        margin-bottom: 1rem;
        line-height: 1.3;
    }

    h3 {
        color: var(--claude-text);
        font-weight: 600;
        font-size: 1.125rem;
        letter-spacing: -0.015em;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        line-height: 1.4;
    }

    h4 {
        color: var(--claude-text);
        font-weight: 600;
        font-size: 1rem;
        letter-spacing: -0.01em;
        line-height: 1.5;
    }

    .main .block-container > div:first-child p {
        color: var(--claude-text-light);
        font-size: 0.9375rem;
        margin-top: 0;
        line-height: 1.6;
    }

    /* Improve list styling */
    ul, ol {
        color: var(--claude-text);
        line-height: 1.8;
    }

    li {
        margin: 0.375rem 0;
    }

    /* Improve link styling */
    a {
        color: var(--claude-orange);
        text-decoration: none;
        transition: color 0.2s ease;
    }

    a:hover {
        color: var(--claude-orange-hover);
        text-decoration: underline;
    }

    /* Welcome Card - Better spacing */
    .title-card {
        background: var(--claude-surface);
        border: 1px solid var(--claude-border);
        border-radius: 12px;
        padding: 2rem;
        margin: 2rem 0;
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

    /* Chat Messages - Better spacing */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        padding: 1.5rem 0 !important;
        margin: 0 !important;
    }

    .stChatMessage > div {
        padding: 0 !important;
    }

    /* Message Content */
    [data-testid="stChatMessageContent"] {
        background: transparent !important;
        padding: 0 !important;
        color: var(--claude-text) !important;
        font-size: 0.9375rem !important;
        line-height: 1.7 !important;
    }

    /* Chat Input Container - Clean & Simple */
    .stChatInput {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 1rem 0 1.5rem;
        background: var(--claude-bg);
        border-top: none !important;
        z-index: 100;
    }

    /* Remove all borders and backgrounds from parent containers */
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

    /* Clean Input Field - Just a simple box */
    .stChatInput textarea {
        width: 100% !important;
        min-height: 52px !important;
        max-height: 200px !important;
        background: var(--claude-surface) !important;
        border: 1px solid var(--claude-border) !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        padding: 14px 50px 14px 16px !important;
        color: var(--claude-text) !important;
        transition: border-color 0.2s ease !important;
        box-shadow: none !important;
        resize: none !important;
        line-height: 24px !important;
        font-family: Inter, sans-serif !important;
        font-weight: 400 !important;
    }

    /* Simple Focus State - Just highlight the border */
    .stChatInput textarea:focus {
        border-color: var(--claude-orange) !important;
        border-width: 2px !important;
        padding: 13px 49px 13px 15px !important;
        box-shadow: none !important;
        outline: none !important;
    }

    /* Simple Hover State */
    .stChatInput textarea:hover:not(:focus) {
        border-color: var(--claude-text-light) !important;
    }

    /* Placeholder Styling */
    .stChatInput textarea::placeholder {
        color: var(--claude-text-light) !important;
        opacity: 0.6;
        font-size: 15px !important;
        font-weight: 400 !important;
    }

    /* Send Button */
    .stChatInput button[kind="primary"] {
        background: var(--claude-orange) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        transition: all 0.2s ease !important;
    }

    .stChatInput button[kind="primary"]:hover {
        background: var(--claude-orange-hover) !important;
    }

    /* Sidebar - Clean Modern Design */
    [data-testid="stSidebar"] {
        background: var(--claude-bg);
        border-right: 1px solid var(--claude-border);
        padding: 0;
        z-index: 999998 !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 0 0.75rem;
    }

    /* Sidebar Header/Title */
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

    /* Section Headers - Smaller, more subtle */
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

    /* Dividers - More subtle */
    [data-testid="stSidebar"] hr {
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        margin: 1.5rem 0;
        opacity: 0.5;
    }

    /* Sidebar Buttons - Clean, minimal style like Claude.ai */
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border: none;
        background: transparent;
        color: var(--claude-text);
        border-radius: 8px;
        padding: 0.625rem 0.75rem;
        font-weight: 500;
        font-size: 0.8125rem;
        transition: all 0.15s ease;
        text-align: left;
        margin: 2px 0;
        position: relative;
        line-height: 1.5;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(217, 119, 87, 0.12);
        color: var(--claude-orange);
        transform: none;
        border: none;
    }

    [data-testid="stSidebar"] .stButton > button:active {
        background: rgba(217, 119, 87, 0.2);
    }

    /* Sidebar spacing improvements */
    [data-testid="stSidebar"] .element-container {
        margin-bottom: 0.125rem;
    }

    [data-testid="stSidebar"] .stMarkdown {
        margin-bottom: 0;
    }

    /* Sidebar scrollbar styling */
    [data-testid="stSidebar"] ::-webkit-scrollbar {
        width: 8px;
    }

    [data-testid="stSidebar"] ::-webkit-scrollbar-track {
        background: transparent;
    }

    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
    }

    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.15);
    }

    /* Main content area buttons - Better hover states */
    .main .stButton > button {
        width: 100%;
        border: 1px solid var(--claude-border);
        background: var(--claude-surface);
        color: var(--claude-text);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        font-weight: 500;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        text-align: left;
    }

    .main .stButton > button:hover {
        background: var(--claude-surface-hover);
        border-color: var(--claude-orange);
        color: var(--claude-orange);
        transform: translateY(-1px);
    }

    /* Expander - Improved styling */
    .streamlit-expanderHeader {
        background: var(--claude-surface) !important;
        border: 1px solid var(--claude-border) !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        color: var(--claude-text) !important;
        padding: 0.875rem 1rem !important;
        transition: all 0.2s ease !important;
    }

    .streamlit-expanderHeader:hover {
        border-color: var(--claude-orange) !important;
        background: var(--claude-surface-hover) !important;
    }

    .streamlit-expanderContent {
        background: var(--claude-surface-hover) !important;
        border: 1px solid var(--claude-border) !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
        padding: 1rem !important;
    }

    /* Tabs - Cleaner design */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 1px solid var(--claude-border);
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

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--claude-text);
        background: transparent;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        border-bottom-color: var(--claude-orange);
        color: var(--claude-orange);
    }

    /* Alerts - Better visual hierarchy */
    .stAlert {
        border-radius: 10px;
        border: 1px solid var(--claude-border);
        background: var(--claude-surface);
        font-size: 0.875rem;
        color: var(--claude-text);
        padding: 0.875rem 1rem;
    }

    /* Dataframes - Cleaner styling */
    .stDataFrame {
        border: 1px solid var(--claude-border);
        border-radius: 10px;
        overflow: hidden;
        font-size: 0.875rem;
    }

    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: var(--claude-surface);
    }

    /* Download Button - Better visual feedback */
    .stDownloadButton > button {
        background: var(--claude-orange) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        font-size: 0.875rem;
        transition: all 0.2s ease;
    }

    .stDownloadButton > button:hover {
        background: var(--claude-orange-hover) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(212, 148, 122, 0.3);
    }

    /* Metrics - Modern card design */
    [data-testid="stMetric"] {
        background: var(--claude-surface);
        border: 1px solid var(--claude-border);
        border-radius: 10px;
        padding: 1.25rem;
        transition: all 0.2s ease;
    }

    [data-testid="stMetric"]:hover {
        border-color: var(--claude-border-light);
        transform: translateY(-2px);
    }

    [data-testid="stMetricValue"] {
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--claude-orange);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.75rem;
        color: var(--claude-text-light);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    /* Loading Spinner */
    .stSpinner > div {
        border-top-color: var(--claude-orange) !important;
    }

    /* Info boxes in sidebar */
    [data-testid="stSidebar"] .stAlert {
        background: var(--claude-surface-hover);
        border-left: 3px solid var(--claude-orange);
        font-size: 0.8125rem;
    }

    /* Code blocks - Improved readability */
    code {
        background: var(--claude-surface-hover) !important;
        color: var(--claude-orange) !important;
        padding: 0.2em 0.4em !important;
        border-radius: 4px !important;
        font-size: 0.875em !important;
    }

    pre {
        background: var(--claude-surface) !important;
        border: 1px solid var(--claude-border) !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }

    pre code {
        background: transparent !important;
        color: var(--claude-text) !important;
    }

    /* Scrollbar - Subtle styling */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: var(--claude-bg);
    }

    ::-webkit-scrollbar-thumb {
        background: #4A4A4A;
        border-radius: 5px;
        border: 2px solid var(--claude-bg);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #5A5A5A;
    }

    /* Loading messages */
    .stMarkdown strong {
        color: var(--claude-orange);
    }

    /* Smooth animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .stChatMessage {
        animation: fadeIn 0.3s ease-out;
    }

    /* File uploader - Better styling */
    [data-testid="stFileUploader"] {
        border: 2px dashed var(--claude-border);
        border-radius: 10px;
        padding: 1.5rem;
        background: var(--claude-surface);
        transition: all 0.2s ease;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--claude-orange);
        background: var(--claude-surface-hover);
    }

    /* Slider - Improved styling */
    .stSlider {
        padding: 1rem 0;
    }

    /* Radio buttons - Better spacing */
    .stRadio > div {
        gap: 0.75rem;
    }

    /* Columns - Better gap management */
    [data-testid="column"] {
        padding: 0 0.75rem;
    }

    [data-testid="column"]:first-child {
        padding-left: 0;
    }

    [data-testid="column"]:last-child {
        padding-right: 0;
    }

    /* Style Streamlit's default sidebar collapse button */
    [data-testid="collapsedControl"] {
        background: var(--claude-surface) !important;
        border: 1px solid var(--claude-border) !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        transition: all 0.2s ease !important;
        z-index: 999999 !important;
    }

    [data-testid="collapsedControl"]:hover {
        background: var(--claude-surface-hover) !important;
        border-color: var(--claude-orange) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12) !important;
        transform: scale(1.05) !important;
    }

    [data-testid="collapsedControl"] svg {
        stroke: var(--claude-text) !important;
    }

    [data-testid="collapsedControl"]:hover svg {
        stroke: var(--claude-orange) !important;
    }

    /* Improved spacing for form elements */
    .stTextInput, .stNumberInput, .stSelectbox {
        margin-bottom: 1rem;
    }

    /* Better image display */
    img {
        border-radius: 8px;
    }

    /* Plotly charts - Dark theme integration */
    .js-plotly-plot {
        border-radius: 10px;
        overflow: hidden;
    }
</style>
"""
