"""
NestScope Help & Documentation
Comprehensive guide to using the NestScope platform
"""

import streamlit as st
from components import init_page, render_header, render_sidebar

# Initialize page with shared layout
init_page(page_title="Help - NestScope", page_icon="❓", layout="wide")

# Render shared header
render_header(page_name="Help & Documentation")

# Add custom CSS for proper scrolling in tabs
st.markdown("""
<style>
    /* Fix tab content scrolling */
    .stTabs [data-baseweb="tab-panel"] {
        max-height: calc(100vh - 200px);
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 0.5rem;
    }

    /* Add padding at bottom of tab content */
    .stTabs [data-baseweb="tab-panel"] > div {
        padding-bottom: 3rem;
    }

    /* Improve scrollbar visibility */
    .stTabs [data-baseweb="tab-panel"]::-webkit-scrollbar {
        width: 10px;
    }

    .stTabs [data-baseweb="tab-panel"]::-webkit-scrollbar-track {
        background: var(--claude-bg);
        border-radius: 5px;
    }

    .stTabs [data-baseweb="tab-panel"]::-webkit-scrollbar-thumb {
        background: #4A4A4A;
        border-radius: 5px;
        border: 2px solid var(--claude-bg);
    }

    .stTabs [data-baseweb="tab-panel"]::-webkit-scrollbar-thumb:hover {
        background: #5A5A5A;
    }

    /* Help content styling */
    .help-section {
        background: var(--claude-surface);
        border: 1px solid var(--claude-border);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .help-section h3 {
        color: var(--claude-orange);
        margin-top: 0;
        margin-bottom: 1rem;
    }

    .help-section h4 {
        color: var(--claude-text);
        margin-top: 1.25rem;
        margin-bottom: 0.75rem;
    }

    .help-section p {
        color: var(--claude-text-light);
        line-height: 1.7;
        margin-bottom: 0.75rem;
    }

    .help-section ul, .help-section ol {
        color: var(--claude-text);
        line-height: 1.8;
        margin-left: 1.5rem;
    }

    .help-section code {
        background: var(--claude-bg) !important;
        color: var(--claude-orange) !important;
        padding: 0.2em 0.4em !important;
        border-radius: 4px !important;
        font-size: 0.875em !important;
    }

    .tip-box {
        background: rgba(217, 119, 87, 0.1);
        border-left: 3px solid var(--claude-orange);
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }

    .warning-box {
        background: rgba(255, 193, 7, 0.1);
        border-left: 3px solid #FFC107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }

    .info-box {
        background: rgba(33, 150, 243, 0.1);
        border-left: 3px solid #2196F3;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Render sidebar
with st.sidebar:
    render_sidebar(active_page="help")

# Main content
st.title("Help & Documentation")
st.caption("Comprehensive guide to using NestScope's avian monitoring platform")

# Create tabs for different sections
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📖 Overview",
    "💬 NestChat Guide",
    "🦅 NestVision Guide",
    "🗄️ NestDB Guide",
    "🧑‍🔬 Nestperts Guide",
    "🔧 Troubleshooting",
    "📚 Technical Reference"
])

# ============================================================================
# TAB 1: OVERVIEW
# ============================================================================

with tab1:
    st.markdown("""
        <div class="title-card">
            <h3>Welcome to NestScope</h3>
            <p>
                NestScope is an AI-powered platform for Gulf Coast avian monitoring and analytics.
                This comprehensive guide will help you get the most out of every feature.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>What is NestScope?</h3>
        <p>
            NestScope combines natural language processing, computer vision, and traditional database management
            to provide a complete toolkit for analyzing Gulf Coast bird colony data from 2010-2021.
        </p>
        <p>
            The platform covers five states (Texas, Louisiana, Mississippi, Alabama, and Florida) and includes
            data from hundreds of colonies and thousands of observations.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Platform Components</h3>

        <h4>🦅 Core Modules</h4>
        <ul>
            <li><strong>NestChat</strong> - Natural language interface for querying bird data</li>
            <li><strong>NestVision</strong> - AI-powered bird detection and counting in images</li>
            <li><strong>NestDB</strong> - Database management interface with version control</li>
            <li><strong>Nestperts</strong> - Expert annotation platform for training data</li>
            <li><strong>Flood Intelligence</strong> - Multi-modal flood hazard monitoring</li>
        </ul>

        <h4>🎯 Key Features</h4>
        <ul>
            <li>Ask questions in plain English and get instant visualizations</li>
            <li>Upload colony images for automatic bird detection</li>
            <li>View and edit database records with full version control</li>
            <li>Create expert-labeled datasets for model training</li>
            <li>Export data and images for external analysis</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Quick Start Workflow</h3>

        <h4>For Data Analysis</h4>
        <ol>
            <li>Open <strong>NestChat</strong> from the sidebar</li>
            <li>Ask a question like "How many birds were observed in Texas in 2020?"</li>
            <li>Review the generated SQL query and results</li>
            <li>Explore interactive charts and maps</li>
            <li>Download results as CSV if needed</li>
        </ol>

        <h4>For Image Analysis</h4>
        <ol>
            <li>Open <strong>NestVision</strong> from the sidebar</li>
            <li>Upload a colony image (JPEG, PNG, or TIFF)</li>
            <li>Choose detection mode: Swift (fast) or Apex (accurate)</li>
            <li>Click "Run Detection" and wait for results</li>
            <li>Review detections and species breakdown</li>
            <li>Download annotated images or send to Nestperts for refinement</li>
        </ol>

        <h4>For Database Management</h4>
        <ol>
            <li>Click "NestDB" in the sidebar to open in new window</li>
            <li>Browse tables in the Table Browser tab</li>
            <li>Toggle Edit Mode to modify records</li>
            <li>Changes are automatically versioned</li>
            <li>Use Version History to view or rollback changes</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Dataset Overview</h3>
        <p>
            The NestScope database contains comprehensive Gulf Coast bird colony survey data:
        </p>
        <ul>
            <li><strong>Time Period:</strong> 2010-2021 (12 years of surveys)</li>
            <li><strong>Geographic Coverage:</strong> Texas, Louisiana, Mississippi, Alabama, Florida</li>
            <li><strong>Primary Species:</strong> 20+ seabird and wading bird species</li>
            <li><strong>Observation Types:</strong> Bird counts, nest counts, colony locations</li>
            <li><strong>Data Sources:</strong> Aerial surveys, ground surveys, photo documentation</li>
        </ul>

        <div class="tip-box">
            <strong>💡 Tip:</strong> The main count data is in <code>tblColonyTotals2010-2021_MayJuneCombined</code>.
            This table contains pre-aggregated bird and nest counts for each colony, year, and species.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>System Requirements</h3>

        <h4>Supported Browsers</h4>
        <ul>
            <li>Google Chrome (recommended)</li>
            <li>Firefox</li>
            <li>Safari</li>
            <li>Microsoft Edge</li>
        </ul>

        <h4>Image Requirements (NestVision)</h4>
        <ul>
            <li><strong>Formats:</strong> JPEG, PNG, TIFF</li>
            <li><strong>Max Size:</strong> 200 MB per image</li>
            <li><strong>Resolution:</strong> Any (automatically scaled for processing)</li>
            <li><strong>Color:</strong> RGB color images work best</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# TAB 2: NESTCHAT GUIDE
# ============================================================================

with tab2:
    st.markdown("""
        <div class="title-card">
            <h3>NestChat - Natural Language Data Interface</h3>
            <p>
                Ask questions in plain English and get instant answers with visualizations.
                NestChat uses AI to convert your questions into SQL queries and generate insights.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>How NestChat Works</h3>
        <p>
            NestChat is powered by a large language model that understands the structure of the bird survey database.
            Here's the process:
        </p>
        <ol>
            <li><strong>You ask a question</strong> in natural language</li>
            <li><strong>AI generates SQL</strong> based on database schema and your question</li>
            <li><strong>Query executes</strong> against the SQLite database</li>
            <li><strong>AI analyzes results</strong> and generates a natural language answer</li>
            <li><strong>Visualizations appear</strong> (charts, maps) based on data type</li>
        </ol>

        <div class="info-box">
            <strong>ℹ️ Under the Hood:</strong> NestChat uses an enhanced metadata system that helps the AI
            understand the difference between bird counts (observations) and photo records, ensuring accurate responses.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Example Questions</h3>

        <h4>Population & Trends</h4>
        <ul>
            <li>"How many Brown Pelicans were observed in 2020?"</li>
            <li>"Show me the trend of Royal Tern populations from 2010 to 2021"</li>
            <li>"Which species had the biggest population increase?"</li>
            <li>"What were the total bird observations by year?"</li>
            <li>"Compare Laughing Gull counts between 2015 and 2020"</li>
        </ul>

        <h4>Geographic Queries</h4>
        <ul>
            <li>"List all colonies in Louisiana"</li>
            <li>"Which state has the most bird colonies?"</li>
            <li>"Show me colony locations on a map"</li>
            <li>"What colonies are between latitude 29 and 30?"</li>
            <li>"Find colonies within 50km of New Orleans"</li>
        </ul>

        <h4>Colony-Specific</h4>
        <ul>
            <li>"What species are found at Queen Bess Island?"</li>
            <li>"Show population changes at Rabbit Island over time"</li>
            <li>"Which colony has the highest bird count in 2021?"</li>
            <li>"List the top 10 colonies by total bird observations"</li>
            <li>"What's the species diversity at each colony?"</li>
        </ul>

        <h4>Species-Specific</h4>
        <ul>
            <li>"Where do Black Skimmers nest?"</li>
            <li>"Show me all observations of Reddish Egrets"</li>
            <li>"Which colonies have both pelicans and terns?"</li>
            <li>"What's the average flock size for Sandwich Terns?"</li>
            <li>"Compare nest counts vs bird counts for Royal Terns"</li>
        </ul>

        <div class="tip-box">
            <strong>💡 Pro Tip:</strong> Be specific about whether you want bird counts or nest counts.
            For example: "How many Royal Tern NESTS were counted in 2020?"
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Understanding Visualizations</h3>

        <h4>Automatic Chart Selection</h4>
        <p>
            NestChat automatically chooses the best visualization based on your query results:
        </p>
        <ul>
            <li><strong>Line Charts:</strong> Time-series data (trends over years)</li>
            <li><strong>Bar Charts:</strong> Comparisons (top colonies, species rankings)</li>
            <li><strong>Maps:</strong> Geographic data (colony locations)</li>
            <li><strong>Tables:</strong> Detailed records and multi-column results</li>
        </ul>

        <h4>Interactive Features</h4>
        <ul>
            <li><strong>Hover:</strong> See exact values on charts</li>
            <li><strong>Zoom:</strong> Click and drag to zoom into chart regions</li>
            <li><strong>Pan:</strong> Move around on maps</li>
            <li><strong>Legend:</strong> Click to show/hide data series</li>
            <li><strong>Download:</strong> Export charts as PNG images</li>
        </ul>

        <h4>Map Features</h4>
        <ul>
            <li><strong>Markers:</strong> Each colony appears as a circle</li>
            <li><strong>Size:</strong> Marker size represents bird count</li>
            <li><strong>Popup:</strong> Click markers for colony details</li>
            <li><strong>Layers:</strong> Toggle between map styles</li>
            <li><strong>Zoom:</strong> Scroll to zoom, drag to pan</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Working with Results</h3>

        <h4>SQL Query Display</h4>
        <p>
            Every NestChat response shows the generated SQL query in a collapsible section.
            This helps you:
        </p>
        <ul>
            <li>Understand exactly what data was retrieved</li>
            <li>Learn SQL by seeing examples</li>
            <li>Verify the query matches your intent</li>
            <li>Copy the query for use in NestDB SQL Editor</li>
        </ul>

        <h4>Exporting Data</h4>
        <p>To export NestChat results:</p>
        <ol>
            <li>Scroll to the results table</li>
            <li>Click the "Download CSV" button</li>
            <li>Open in Excel, Google Sheets, or other tools</li>
        </ol>

        <h4>Conversation History</h4>
        <p>
            NestChat maintains conversation context, so you can ask follow-up questions:
        </p>
        <ul>
            <li>"Show me the same data for 2019"</li>
            <li>"Now break it down by species"</li>
            <li>"What about Louisiana only?"</li>
        </ul>

        <div class="warning-box">
            <strong>⚠️ Note:</strong> Conversation history is stored in browser memory and will reset
            if you refresh the page or switch to another page.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Tips for Better Results</h3>

        <h4>Be Specific</h4>
        <ul>
            <li><strong>Instead of:</strong> "Tell me about birds"</li>
            <li><strong>Try:</strong> "How many Brown Pelican observations were recorded in Texas in 2020?"</li>
        </ul>

        <h4>Use Correct Species Names</h4>
        <ul>
            <li>Use full species names: "Royal Tern" not "Tern"</li>
            <li>Check spelling: "Laughing Gull" not "Laughing Gul"</li>
            <li>Refer to Technical Reference tab for full species list</li>
        </ul>

        <h4>Specify Time Ranges</h4>
        <ul>
            <li>"...in 2020" (single year)</li>
            <li>"...from 2015 to 2021" (range)</li>
            <li>"...between 2018 and 2020" (inclusive range)</li>
        </ul>

        <h4>Request Visualizations</h4>
        <ul>
            <li>"Show me a chart of..."</li>
            <li>"Plot the trend..."</li>
            <li>"Display on a map..."</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Common Issues & Solutions</h3>

        <h4>"No results found"</h4>
        <p><strong>Possible causes:</strong></p>
        <ul>
            <li>Misspelled species or colony name</li>
            <li>Year outside 2010-2021 range</li>
            <li>State abbreviation instead of full name (use "Texas" not "TX")</li>
        </ul>

        <h4>"Query failed" or error messages</h4>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Rephrase your question more clearly</li>
            <li>Break complex questions into simpler parts</li>
            <li>Check that you're using correct table/column names</li>
        </ul>

        <h4>Unexpected results</h4>
        <p><strong>Check:</strong></p>
        <ul>
            <li>Review the generated SQL query</li>
            <li>Verify you asked for birds vs nests</li>
            <li>Confirm the time period in your question</li>
            <li>Make sure species name is correct</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# TAB 3: NESTVISION GUIDE
# ============================================================================

with tab3:
    st.markdown("""
        <div class="title-card">
            <h3>NestVision - AI Bird Detection & Counting</h3>
            <p>
                Upload colony images and use computer vision to automatically detect and count birds.
                NestVision uses YOLO-based object detection models optimized for aerial bird imagery.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>How NestVision Works</h3>
        <p>
            NestVision uses state-of-the-art computer vision technology to detect birds in images:
        </p>
        <ol>
            <li><strong>Image Upload:</strong> You upload a colony image</li>
            <li><strong>Preprocessing:</strong> Image is resized and normalized</li>
            <li><strong>Detection:</strong> YOLO model identifies bird locations</li>
            <li><strong>Classification:</strong> Each bird is classified into species groups</li>
            <li><strong>Post-processing:</strong> Results are filtered and refined</li>
            <li><strong>Visualization:</strong> Bounding boxes drawn on image</li>
        </ol>

        <div class="info-box">
            <strong>ℹ️ Technology:</strong> NestVision uses YOLO26 (You Only Look Once) for detection
            and a separate classifier for species grouping. Both models run in ONNX format for fast inference.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Detection Modes</h3>

        <h4>🚀 Swift Mode (Default)</h4>
        <p>
            Fast inference mode optimized for speed:
        </p>
        <ul>
            <li><strong>Speed:</strong> ~3x faster than Apex</li>
            <li><strong>Accuracy:</strong> Excellent for most images</li>
            <li><strong>Use Case:</strong> Quick previews, real-time processing</li>
            <li><strong>Model:</strong> Lightweight YOLO variant</li>
        </ul>

        <h4>🎯 Apex Mode</h4>
        <p>
            Maximum accuracy mode for detailed analysis:
        </p>
        <ul>
            <li><strong>Speed:</strong> Slower but more thorough</li>
            <li><strong>Accuracy:</strong> Best for small or distant birds</li>
            <li><strong>Use Case:</strong> Final analysis, expert annotation</li>
            <li><strong>Model:</strong> High-capacity YOLO variant</li>
        </ul>

        <h4>SAHI (Slicing Aided Hyper Inference)</h4>
        <p>
            For large images (>1024px), NestVision automatically uses SAHI:
        </p>
        <ul>
            <li>Slices image into overlapping tiles</li>
            <li>Processes each tile independently</li>
            <li>Merges detections with 20% overlap</li>
            <li>Improves detection of small objects</li>
        </ul>

        <div class="tip-box">
            <strong>💡 Recommendation:</strong> Start with Swift mode for speed. Switch to Apex mode
            if you need higher accuracy or are working with challenging images (high altitude, small birds).
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Species Classification</h3>

        <p>
            NestVision classifies detected birds into 7 species groups:
        </p>
        <ul>
            <li><strong>COLOR_WADER:</strong> Roseate Spoonbills, Reddish Egrets</li>
            <li><strong>DARK:</strong> Double-crested Cormorants, Neotropic Cormorants</li>
            <li><strong>GULL:</strong> Laughing Gulls, other gull species</li>
            <li><strong>PELICAN:</strong> Brown Pelicans, American White Pelicans</li>
            <li><strong>SHOREBIRD:</strong> Black Skimmers, American Oystercatchers</li>
            <li><strong>TERN:</strong> Royal Terns, Sandwich Terns, Least Terns, etc.</li>
            <li><strong>WHITE_WADER:</strong> Great Egrets, Snowy Egrets, White Ibis, etc.</li>
        </ul>

        <h4>Color-Coded Boxes</h4>
        <p>Each species group has a unique color for easy identification:</p>
        <ul>
            <li><strong style="color: #FF1493;">Pink:</strong> COLOR_WADER</li>
            <li><strong style="color: #2F4F4F;">Dark Gray:</strong> DARK</li>
            <li><strong style="color: #F0F0F0;">Light Gray:</strong> GULL</li>
            <li><strong style="color: #CD853F;">Tan:</strong> PELICAN</li>
            <li><strong style="color: #FFD700;">Gold:</strong> SHOREBIRD</li>
            <li><strong style="color: #FFFFFF;">White:</strong> TERN</li>
            <li><strong style="color: #FAFAFA;">Off-White:</strong> WHITE_WADER</li>
        </ul>

        <div class="warning-box">
            <strong>⚠️ Note:</strong> Classification is at the group level, not individual species.
            For precise species identification, use Nestperts for expert annotation.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Step-by-Step Workflow</h3>

        <h4>1. Prepare Your Image</h4>
        <ul>
            <li>Ensure image is in JPEG, PNG, or TIFF format</li>
            <li>Check that birds are visible (not too small or blurry)</li>
            <li>Images can be any size (will be scaled automatically)</li>
            <li>RGB color images work best</li>
        </ul>

        <h4>2. Upload Image</h4>
        <ul>
            <li>Click "Browse files" or drag and drop</li>
            <li>Wait for image preview to appear</li>
            <li>Verify correct image is loaded</li>
        </ul>

        <h4>3. Configure Settings</h4>
        <ul>
            <li><strong>Detection Mode:</strong> Choose Swift or Apex</li>
            <li><strong>Confidence Threshold:</strong> Adjust slider (default: 0.25)</li>
            <li>Higher threshold = fewer false positives but might miss birds</li>
            <li>Lower threshold = more detections but more false positives</li>
        </ul>

        <h4>4. Run Detection</h4>
        <ul>
            <li>Click "Run Detection" button</li>
            <li>Wait for processing (10-60 seconds depending on image size)</li>
            <li>Progress indicator shows status</li>
        </ul>

        <h4>5. Review Results</h4>
        <ul>
            <li><strong>Total Count:</strong> Number of birds detected</li>
            <li><strong>Species Breakdown:</strong> Bar chart showing counts by group</li>
            <li><strong>Annotated Image:</strong> Original image with colored boxes</li>
            <li><strong>Inference Time:</strong> How long processing took</li>
        </ul>

        <h4>6. Export or Refine</h4>
        <ul>
            <li><strong>Download Image:</strong> Save annotated image with boxes</li>
            <li><strong>Train with Experts:</strong> Send to Nestperts for refinement</li>
            <li><strong>Adjust Settings:</strong> Try different threshold or mode</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Confidence Threshold Explained</h3>

        <p>
            The confidence threshold determines which detections are kept:
        </p>

        <h4>Default: 0.25 (25%)</h4>
        <ul>
            <li>Balanced setting for most images</li>
            <li>Keeps detections with >25% confidence</li>
            <li>Good for typical colony images</li>
        </ul>

        <h4>Low: 0.10-0.20 (10-20%)</h4>
        <ul>
            <li>More sensitive detection</li>
            <li>Good for distant or small birds</li>
            <li>May include false positives (rocks, debris)</li>
            <li><strong>Use when:</strong> Birds are far away or image quality is poor</li>
        </ul>

        <h4>High: 0.40-0.60 (40-60%)</h4>
        <ul>
            <li>More conservative detection</li>
            <li>Reduces false positives</li>
            <li>May miss some real birds</li>
            <li><strong>Use when:</strong> Image has many distractors or you need precision</li>
        </ul>

        <div class="tip-box">
            <strong>💡 Pro Tip:</strong> If you get too many false detections, increase the threshold.
            If birds are being missed, decrease it. Run multiple times to find the sweet spot.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Best Practices</h3>

        <h4>Image Quality</h4>
        <ul>
            <li><strong>Resolution:</strong> Higher resolution = better detection</li>
            <li><strong>Lighting:</strong> Well-lit images work best</li>
            <li><strong>Contrast:</strong> Birds should contrast with background</li>
            <li><strong>Focus:</strong> Sharp images perform better than blurry</li>
        </ul>

        <h4>Camera Angle</h4>
        <ul>
            <li><strong>Overhead:</strong> Best for accurate counts</li>
            <li><strong>Oblique:</strong> Works but may miss overlapping birds</li>
            <li><strong>Ground-level:</strong> Challenging, consider manual counting</li>
        </ul>

        <h4>Colony Density</h4>
        <ul>
            <li><strong>Sparse:</strong> High accuracy expected</li>
            <li><strong>Moderate:</strong> Good accuracy with proper threshold</li>
            <li><strong>Dense:</strong> May undercount due to overlap, use Apex mode</li>
        </ul>

        <h4>Validation</h4>
        <ul>
            <li>Always visually inspect results</li>
            <li>Compare counts to ground truth if available</li>
            <li>Use Nestperts for expert validation</li>
            <li>Document any systematic errors</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Troubleshooting</h3>

        <h4>Too Many False Positives</h4>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Increase confidence threshold to 0.35-0.45</li>
            <li>Switch to Apex mode for better discrimination</li>
            <li>Check if image has many rocks/debris that look like birds</li>
        </ul>

        <h4>Missing Birds</h4>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Decrease confidence threshold to 0.15-0.20</li>
            <li>Switch to Apex mode for better small object detection</li>
            <li>Verify image quality is sufficient</li>
            <li>Check if birds are extremely small in frame</li>
        </ul>

        <h4>Slow Processing</h4>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Use Swift mode instead of Apex</li>
            <li>Resize very large images (>10 MP) before upload</li>
            <li>Process fewer images at once</li>
            <li>Check system status for backend issues</li>
        </ul>

        <h4>Wrong Species Classification</h4>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Remember classification is at group level, not species level</li>
            <li>Use Nestperts for precise species identification</li>
            <li>Check if lighting affects bird appearance</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# TAB 4: NESTDB GUIDE
# ============================================================================

with tab4:
    st.markdown("""
        <div class="title-card">
            <h3>NestDB - Database Management Interface</h3>
            <p>
                View, edit, and manage bird survey data with a Supabase-like interface.
                NestDB includes full version control powered by Git.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Accessing NestDB</h3>
        <p>
            NestDB is a separate Flask application running on port 5000:
        </p>
        <ol>
            <li>Click "NestDB" in the Expert Tools section of the sidebar</li>
            <li>Opens in a new browser tab at <code>http://localhost:5000/nestdb</code></li>
            <li>Interface loads with Table Browser as default tab</li>
        </ol>

        <div class="info-box">
            <strong>ℹ️ Architecture:</strong> NestDB runs separately from the main Streamlit app to provide
            unrestricted database access while keeping the main app secure (read-only).
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Table Browser</h3>

        <h4>Viewing Tables</h4>
        <ol>
            <li>Select a table from the dropdown</li>
            <li>Data loads automatically (50 rows per page by default)</li>
            <li>Use pagination controls to navigate pages</li>
            <li>Adjust "Rows per page" for more/fewer results</li>
        </ol>

        <h4>Edit Mode</h4>
        <p>Toggle Edit Mode to modify data:</p>
        <ul>
            <li><strong>Off (View Mode):</strong> Read-only display</li>
            <li><strong>On (Edit Mode):</strong> Click cells to edit values</li>
        </ul>

        <h4>Editing Data</h4>
        <ol>
            <li>Toggle Edit Mode ON</li>
            <li>Click any cell to edit (except primary keys)</li>
            <li>Make changes to values</li>
            <li>Click "Save Changes" button when done</li>
            <li>Changes are automatically versioned (Git commit created)</li>
        </ol>

        <h4>Adding Rows</h4>
        <ol>
            <li>Toggle Edit Mode ON</li>
            <li>Click "Add New Row" button</li>
            <li>Fill in values for each column</li>
            <li>Required fields marked with *</li>
            <li>Click "Insert Row" to save</li>
            <li>New row automatically versioned</li>
        </ol>

        <div class="warning-box">
            <strong>⚠️ Important:</strong> Primary key columns (marked with 🔑) cannot be edited.
            They are set automatically or must be unique.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Schema Viewer</h3>

        <p>
            The Schema Viewer shows the structure of database tables:
        </p>

        <h4>Column Information</h4>
        <ul>
            <li><strong>Column Name:</strong> Field identifier</li>
            <li><strong>Type:</strong> Data type (INTEGER, TEXT, REAL, etc.)</li>
            <li><strong>PK:</strong> 🔑 indicates primary key</li>
            <li><strong>Required:</strong> ✓ means NOT NULL (required field)</li>
            <li><strong>Default Value:</strong> Auto-filled value if not provided</li>
        </ul>

        <h4>Using Schema Information</h4>
        <ul>
            <li>Understand table structure before editing</li>
            <li>Identify primary keys (cannot be edited)</li>
            <li>See which fields are required</li>
            <li>Check data types for correct formatting</li>
            <li>Export schema as CSV for documentation</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>SQL Query Editor</h3>

        <p>
            Execute custom SQL queries for advanced data exploration:
        </p>

        <h4>Writing Queries</h4>
        <ul>
            <li>Use standard SQLite syntax</li>
            <li>SELECT statements recommended (read-only)</li>
            <li>Supports JOINs, subqueries, CTEs, aggregations</li>
            <li>Comments allowed (-- single line, /* multi-line */)</li>
        </ul>

        <h4>Example Queries Provided</h4>
        <p>Click "Example Queries" expander to see:</p>
        <ul>
            <li>Basic SELECT statements</li>
            <li>GROUP BY aggregations</li>
            <li>JOINs across tables</li>
            <li>Window functions</li>
            <li>Complex analytical queries</li>
        </ul>

        <h4>Query History</h4>
        <ul>
            <li>Last 10 queries saved automatically</li>
            <li>Click "Reuse" to load a previous query</li>
            <li>Click "Remove" to delete from history</li>
        </ul>

        <h4>Exporting Results</h4>
        <ul>
            <li>Results display as interactive table</li>
            <li>Click "Download Results" for CSV export</li>
            <li>Open in Excel, R, Python, etc.</li>
        </ul>

        <div class="tip-box">
            <strong>💡 Pro Tip:</strong> Copy queries from NestChat's SQL display and paste them here
            for modification and re-execution.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Version History (Git-Based)</h3>

        <p>
            All database changes are tracked with Git version control:
        </p>

        <h4>Automatic Versioning</h4>
        <ul>
            <li>Every save creates a Git commit</li>
            <li>Commit includes SQL dump of entire database</li>
            <li>Timestamp and author recorded</li>
            <li>Full audit trail maintained</li>
        </ul>

        <h4>Creating Manual Checkpoints</h4>
        <ol>
            <li>Enter your email in "Your email" field (saved for future use)</li>
            <li>Type a checkpoint description</li>
            <li>Click "Save Checkpoint"</li>
            <li>Checkpoint appears in commit timeline</li>
        </ol>

        <h4>Viewing Commit History</h4>
        <ul>
            <li><strong>Current Version:</strong> Marked with 🟢 green dot</li>
            <li><strong>Recent Commits:</strong> Marked with 🔵 blue dot</li>
            <li><strong>Older Commits:</strong> Marked with ⚪ white dot</li>
            <li>Each commit shows: hash, date, message, author</li>
        </ul>

        <h4>Viewing Changes (Diff)</h4>
        <ol>
            <li>Expand a commit in the timeline</li>
            <li>Click "View Changes" button</li>
            <li>See SQL diff showing what changed</li>
            <li>Lines starting with + are additions</li>
            <li>Lines starting with - are deletions</li>
        </ol>

        <h4>Rolling Back</h4>
        <ol>
            <li>Expand the commit you want to restore</li>
            <li>Click "Rollback Here" button</li>
            <li>Read the warning carefully</li>
            <li>Click "Confirm Rollback"</li>
            <li>Database restored to that state</li>
            <li>Safety snapshot created automatically</li>
            <li>Rollback recorded as new commit</li>
        </ol>

        <div class="warning-box">
            <strong>⚠️ Rollback Warning:</strong> Rolling back will undo ALL changes made after that commit.
            A safety snapshot is created, but use this feature carefully. Consider creating a manual checkpoint first.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Best Practices</h3>

        <h4>Before Editing</h4>
        <ul>
            <li>Create a manual checkpoint: "Before bulk species update"</li>
            <li>Review schema to understand constraints</li>
            <li>Test queries in SQL Editor first</li>
            <li>Make a backup if doing major changes</li>
        </ul>

        <h4>During Editing</h4>
        <ul>
            <li>Edit in small batches (easier to review and rollback)</li>
            <li>Use clear, descriptive commit messages</li>
            <li>Include your email for proper attribution</li>
            <li>Verify changes immediately after saving</li>
        </ul>

        <h4>After Editing</h4>
        <ul>
            <li>Review the commit in Version History</li>
            <li>Check the diff to ensure changes are correct</li>
            <li>Test queries against modified data</li>
            <li>Document significant changes externally</li>
        </ul>

        <h4>Collaboration</h4>
        <ul>
            <li>Always use your real email for accountability</li>
            <li>Write descriptive commit messages</li>
            <li>Create checkpoints before starting work</li>
            <li>Communicate major changes to team</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Common Tasks</h3>

        <h4>Correcting a Wrong Value</h4>
        <ol>
            <li>Go to Table Browser</li>
            <li>Select the table with incorrect data</li>
            <li>Find the row (use pagination or filters)</li>
            <li>Toggle Edit Mode</li>
            <li>Click the cell and change the value</li>
            <li>Click "Save Changes"</li>
        </ol>

        <h4>Adding New Survey Data</h4>
        <ol>
            <li>Create manual checkpoint: "Before adding 2022 data"</li>
            <li>Go to Table Browser</li>
            <li>Select appropriate table</li>
            <li>Toggle Edit Mode</li>
            <li>Click "Add New Row"</li>
            <li>Fill in all required fields</li>
            <li>Click "Insert Row"</li>
            <li>Repeat for additional rows</li>
        </ol>

        <h4>Bulk Analysis Query</h4>
        <ol>
            <li>Go to SQL Query Editor</li>
            <li>Write your analytical query</li>
            <li>Click "Execute Query"</li>
            <li>Review results</li>
            <li>Download as CSV if needed</li>
        </ol>

        <h4>Undoing Recent Changes</h4>
        <ol>
            <li>Go to Version History</li>
            <li>Find commit just before the mistake</li>
            <li>Click "Rollback Here"</li>
            <li>Confirm rollback</li>
            <li>Verify data is restored</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# TAB 5: NESTPERTS GUIDE
# ============================================================================

with tab5:
    st.markdown("""
        <div class="title-card">
            <h3>Nestperts - Expert Species Training Platform</h3>
            <p>
                Create expert-labeled datasets for training species classification models.
                Uses MobileSAM for interactive segmentation and supports multi-expert workflows.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>What is Nestperts?</h3>
        <p>
            Nestperts is an expert annotation platform designed for:
        </p>
        <ul>
            <li>Refining AI detections from NestVision</li>
            <li>Creating ground-truth training datasets</li>
            <li>Species-level identification (not just groups)</li>
            <li>Multi-expert collaboration and validation</li>
        </ul>

        <div class="info-box">
            <strong>ℹ️ Purpose:</strong> While NestVision provides automated detection, Nestperts
            enables domain experts to correct errors and add precise species labels for model training.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Getting Started</h3>

        <h4>Accessing Nestperts</h4>
        <ol>
            <li>Click "Nestperts" in Expert Tools section of sidebar</li>
            <li>Opens at <code>http://localhost:5000</code></li>
            <li>Main interface shows image gallery</li>
        </ol>

        <h4>Sending Images from NestVision</h4>
        <ol>
            <li>Run detection in NestVision</li>
            <li>Review results</li>
            <li>Click "Train with Experts" button</li>
            <li>Image and detections sent to Nestperts</li>
            <li>Automatically opens in Nestperts for refinement</li>
        </ol>

        <h4>Manual Upload</h4>
        <ol>
            <li>Open Nestperts directly</li>
            <li>Click "Upload Images" button</li>
            <li>Select one or more images</li>
            <li>Images appear in gallery</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Annotation Workflow</h3>

        <h4>Step 1: Select Image</h4>
        <ul>
            <li>Click an image thumbnail in the gallery</li>
            <li>Image loads in main annotation view</li>
            <li>Existing detections shown as bounding boxes</li>
        </ul>

        <h4>Step 2: Review Existing Detections</h4>
        <ul>
            <li>Check if all birds are detected</li>
            <li>Look for false positives (non-bird detections)</li>
            <li>Verify species classifications are correct</li>
        </ul>

        <h4>Step 3: Add Missing Birds</h4>
        <ol>
            <li>Click on center of undetected bird</li>
            <li>MobileSAM generates segmentation mask</li>
            <li>Bounding box automatically created</li>
            <li>Assign species from dropdown</li>
            <li>Repeat for all missing birds</li>
        </ol>

        <h4>Step 4: Delete False Positives</h4>
        <ol>
            <li>Click on incorrect detection box</li>
            <li>Click "Delete" button</li>
            <li>Confirm deletion</li>
        </ol>

        <h4>Step 5: Correct Species Labels</h4>
        <ol>
            <li>Click on detection box</li>
            <li>Change species in dropdown</li>
            <li>Click "Update" to save</li>
        </ol>

        <h4>Step 6: Save Annotations</h4>
        <ol>
            <li>Click "Save" button</li>
            <li>Labels saved in YOLO format</li>
            <li>Species metadata saved separately</li>
            <li>Progress tracked in project state</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>MobileSAM Segmentation</h3>

        <h4>How It Works</h4>
        <p>
            MobileSAM (Segment Anything Model) automatically segments objects:
        </p>
        <ol>
            <li>You click on a bird</li>
            <li>MobileSAM processes the image around that point</li>
            <li>Generates a segmentation mask</li>
            <li>Bounding box calculated from mask</li>
            <li>5% padding added for better coverage</li>
        </ol>

        <h4>Two Detection Modes</h4>
        <ul>
            <li><strong>Fast Mode:</strong> 720x720 resolution, faster processing</li>
            <li><strong>SAHI Mode:</strong> 1024x1024 resolution, better accuracy</li>
        </ul>

        <h4>Tips for Best Results</h4>
        <ul>
            <li>Click near the center of the bird</li>
            <li>Avoid clicking on overlap between birds</li>
            <li>Use SAHI mode for small or distant birds</li>
            <li>If segmentation fails, try clicking different spot</li>
        </ul>

        <div class="warning-box">
            <strong>⚠️ Limitation:</strong> MobileSAM may struggle with:
            <ul>
                <li>Extremely dense colonies where birds overlap significantly</li>
                <li>Birds that blend into background</li>
                <li>Very small birds (less than 10px)</li>
            </ul>
            In these cases, you may need to manually adjust boxes.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Species List</h3>

        <p>
            Nestperts supports precise species identification. Available species include:
        </p>

        <h4>Pelicans</h4>
        <ul>
            <li>Brown Pelican</li>
            <li>American White Pelican</li>
        </ul>

        <h4>Cormorants</h4>
        <ul>
            <li>Double-crested Cormorant</li>
            <li>Neotropic Cormorant</li>
        </ul>

        <h4>Herons & Egrets (White)</h4>
        <ul>
            <li>Great Egret</li>
            <li>Snowy Egret</li>
            <li>Cattle Egret</li>
        </ul>

        <h4>Herons & Egrets (Colored)</h4>
        <ul>
            <li>Reddish Egret</li>
            <li>Tricolored Heron</li>
            <li>Little Blue Heron</li>
        </ul>

        <h4>Ibises & Spoonbills</h4>
        <ul>
            <li>White Ibis</li>
            <li>White-faced Ibis</li>
            <li>Roseate Spoonbill</li>
        </ul>

        <h4>Terns</h4>
        <ul>
            <li>Royal Tern</li>
            <li>Sandwich Tern</li>
            <li>Least Tern</li>
            <li>Caspian Tern</li>
            <li>Forster's Tern</li>
            <li>Common Tern</li>
            <li>Gull-billed Tern</li>
            <li>Black Tern</li>
        </ul>

        <h4>Gulls</h4>
        <ul>
            <li>Laughing Gull</li>
            <li>Ring-billed Gull</li>
            <li>Herring Gull</li>
        </ul>

        <h4>Shorebirds</h4>
        <ul>
            <li>Black Skimmer</li>
            <li>American Oystercatcher</li>
        </ul>

        <h4>Other</h4>
        <ul>
            <li>Magnificent Frigatebird</li>
            <li>Anhinga</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Multi-Expert Workflow</h3>

        <h4>Expert Roles</h4>
        <ul>
            <li><strong>Primary Annotator:</strong> First pass at labeling</li>
            <li><strong>Reviewer:</strong> Checks and corrects annotations</li>
            <li><strong>Validator:</strong> Final quality check</li>
        </ul>

        <h4>Collaboration Features</h4>
        <ul>
            <li>Project state tracked in <code>project_state.json</code></li>
            <li>Each image tracks who annotated it and when</li>
            <li>Annotation history preserved</li>
            <li>Conflict resolution via discussion</li>
        </ul>

        <h4>Quality Control</h4>
        <ul>
            <li>Mark images as "complete" when finished</li>
            <li>Flag difficult images for group review</li>
            <li>Record confidence levels for uncertain IDs</li>
            <li>Document special cases or anomalies</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Data Output</h3>

        <h4>YOLO Format Labels</h4>
        <p>Saved in <code>labeller/nestvision/labels/</code>:</p>
        <ul>
            <li>One .txt file per image</li>
            <li>Format: <code>class_id x_center y_center width height</code></li>
            <li>Coordinates normalized to 0-1 range</li>
            <li>Class IDs correspond to species</li>
        </ul>

        <h4>Species Metadata</h4>
        <p>Saved in <code>labeller/nestvision/</code>:</p>
        <ul>
            <li><code>classes.txt</code>: List of species names</li>
            <li><code>species_data.json</code>: Detailed species information</li>
            <li>Includes common names, scientific names, groups</li>
        </ul>

        <h4>Training Data Structure</h4>
        <pre>
nestvision/
├── images/           # Original images
├── labels/           # YOLO format labels
├── classes.txt       # Species list
└── species_data.json # Metadata
        </pre>

        <div class="tip-box">
            <strong>💡 Using Training Data:</strong> This format is compatible with YOLO model training.
            Use Ultralytics YOLO or similar frameworks to train custom species classifiers.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Best Practices</h3>

        <h4>Annotation Quality</h4>
        <ul>
            <li>Be consistent with species identification</li>
            <li>Include partial birds at image edges</li>
            <li>Don't annotate severely occluded birds (>50% hidden)</li>
            <li>Use tight bounding boxes (minimal background)</li>
        </ul>

        <h4>Difficult Cases</h4>
        <ul>
            <li>Juveniles: Label as species if identifiable</li>
            <li>Breeding plumage: Use standard species name</li>
            <li>Hybrids: Label as more abundant parent species</li>
            <li>Uncertain ID: Mark for review, use best guess</li>
        </ul>

        <h4>Efficiency Tips</h4>
        <ul>
            <li>Annotate similar images in batches</li>
            <li>Use keyboard shortcuts (if available)</li>
            <li>Take breaks to avoid fatigue errors</li>
            <li>Save frequently to avoid losing work</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# TAB 6: TROUBLESHOOTING
# ============================================================================

with tab6:
    st.markdown("""
        <div class="title-card">
            <h3>Troubleshooting & FAQs</h3>
            <p>
                Solutions to common problems and answers to frequently asked questions.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>General Issues</h3>

        <h4>Page Won't Load</h4>
        <p><strong>Problem:</strong> Blank page or connection error</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Check that all services are running: <code>./run_app.sh</code></li>
            <li>Verify correct URL: <code>http://localhost:8501</code> for main app</li>
            <li>Check System Status page for service health</li>
            <li>Try hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)</li>
            <li>Clear browser cache and cookies</li>
        </ul>

        <h4>Slow Performance</h4>
        <p><strong>Problem:</strong> App is sluggish or unresponsive</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Close unused browser tabs</li>
            <li>Restart the application services</li>
            <li>Check available RAM (NestVision uses 2-4GB)</li>
            <li>Use Swift mode instead of Apex in NestVision</li>
            <li>Reduce image sizes before upload</li>
        </ul>

        <h4>"Backend Connection Failed"</h4>
        <p><strong>Problem:</strong> Cannot reach FastAPI backend</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Check if backend is running: <code>curl http://localhost:8000/health</code></li>
            <li>Check logs: <code>tail -f logs/server.log</code></li>
            <li>Restart backend: Kill process and run <code>./run_app.sh</code></li>
            <li>Verify port 8000 is not blocked by firewall</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>NestChat Issues</h3>

        <h4>"Query Failed" Error</h4>
        <p><strong>Possible causes:</strong></p>
        <ul>
            <li>AI generated invalid SQL</li>
            <li>Referenced non-existent table or column</li>
            <li>Syntax error in generated query</li>
            <li>OpenRouter API key missing or invalid</li>
        </ul>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Rephrase question more clearly</li>
            <li>Check that table/column names exist in schema</li>
            <li>View generated SQL and check for errors</li>
            <li>Verify <code>OPENROUTER_API_KEY</code> in <code>.env</code> file</li>
        </ul>

        <h4>No Visualization Appears</h4>
        <p><strong>Problem:</strong> Results show but no chart/map</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Check if query includes required columns (Latitude/Longitude for maps)</li>
            <li>Verify results have enough rows (some charts need minimum data)</li>
            <li>Refresh page and try again</li>
            <li>Check browser console for JavaScript errors</li>
        </ul>

        <h4>Results Don't Match Expectations</h4>
        <p><strong>Problem:</strong> Count seems wrong or missing data</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Review generated SQL carefully</li>
            <li>Check if AI used correct table (colony_totals vs species_data)</li>
            <li>Verify time period in WHERE clause</li>
            <li>Confirm species name spelling</li>
            <li>Use NestDB SQL Editor to verify with manual query</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>NestVision Issues</h3>

        <h4>Upload Fails</h4>
        <p><strong>Problem:</strong> Image won't upload or error appears</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Check file size (max 200 MB)</li>
            <li>Verify file format (JPEG, PNG, or TIFF only)</li>
            <li>Try renaming file (remove special characters)</li>
            <li>Convert to JPEG if TIFF is problematic</li>
            <li>Check available disk space on server</li>
        </ul>

        <h4>"Detection Failed" Error</h4>
        <p><strong>Problem:</strong> Processing fails during inference</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Check logs: <code>tail -f logs/server.log</code></li>
            <li>Verify ONNX models exist in <code>models/</code> directory</li>
            <li>Try Swift mode if Apex is failing</li>
            <li>Restart backend to clear any stuck processes</li>
            <li>Check available RAM (need 2-4GB free)</li>
        </ul>

        <h4>Processing Takes Forever</h4>
        <p><strong>Problem:</strong> Detection runs for minutes</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Very large images (>10MP) take longer - this is normal</li>
            <li>Switch to Swift mode for faster processing</li>
            <li>Resize image to 4K resolution before upload</li>
            <li>Check if GPU is being used (logs will show)</li>
        </ul>

        <h4>Poor Detection Results</h4>
        <p><strong>Problem:</strong> Missing birds or too many false positives</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Adjust confidence threshold (see NestVision Guide)</li>
            <li>Try Apex mode for better accuracy</li>
            <li>Check image quality (resolution, lighting, focus)</li>
            <li>Verify birds are visible and not too small</li>
            <li>Use Nestperts to correct and improve</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>NestDB Issues</h3>

        <h4>Can't Access NestDB</h4>
        <p><strong>Problem:</strong> Link doesn't open or 404 error</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Verify Flask app is running: <code>curl http://localhost:5000</code></li>
            <li>Check logs: <code>tail -f logs/nestperts.log</code></li>
            <li>Restart Flask app manually: <code>python labeller/app.py</code></li>
            <li>Check port 5000 is not in use by another app</li>
        </ul>

        <h4>Changes Won't Save</h4>
        <p><strong>Problem:</strong> Edit button doesn't work or error on save</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Check that Edit Mode is toggled ON</li>
            <li>Verify you're not editing primary key columns</li>
            <li>Check data type matches column type</li>
            <li>Look for validation errors in logs</li>
            <li>Try refreshing page and re-entering changes</li>
        </ul>

        <h4>Version Control Not Working</h4>
        <p><strong>Problem:</strong> No commits appearing or rollback fails</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Check Git is installed: <code>git --version</code></li>
            <li>Verify <code>data/.git</code> directory exists</li>
            <li>Check disk space for Git operations</li>
            <li>Review logs for Git error messages</li>
            <li>Reinitialize Git repo if corrupted</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Nestperts Issues</h3>

        <h4>MobileSAM Segmentation Fails</h4>
        <p><strong>Problem:</strong> Click doesn't generate bounding box</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Check logs for MobileSAM errors</li>
            <li>Verify <code>mobile_sam.pt</code> model exists</li>
            <li>Try clicking center of bird more precisely</li>
            <li>Switch between Fast and SAHI modes</li>
            <li>Restart Nestperts to clear cache</li>
        </ul>

        <h4>Labels Not Saving</h4>
        <p><strong>Problem:</strong> Annotations lost after reload</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Click "Save" button before closing</li>
            <li>Check write permissions on <code>labeller/nestvision/labels/</code></li>
            <li>Verify disk space available</li>
            <li>Check logs for save errors</li>
        </ul>

        <h4>Species Dropdown Empty</h4>
        <p><strong>Problem:</strong> Can't select species</p>
        <p><strong>Solutions:</strong></p>
        <ul>
            <li>Check <code>classes.txt</code> file exists and has content</li>
            <li>Refresh page to reload species list</li>
            <li>Verify JSON syntax in <code>species_data.json</code></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Frequently Asked Questions</h3>

        <h4>Q: Can I use NestScope offline?</h4>
        <p>
            <strong>A:</strong> Partially. NestVision (computer vision) works offline once models are downloaded.
            NestChat requires OpenRouter API connection for LLM queries. NestDB and Nestperts work offline.
        </p>

        <h4>Q: What's the difference between observations and records?</h4>
        <p>
            <strong>A:</strong> "Observations" refers to individual bird counts. "Records" refers to photo
            database entries. For bird counts, use the <code>tblColonyTotals</code> table.
        </p>

        <h4>Q: Can I add my own data to the database?</h4>
        <p>
            <strong>A:</strong> Yes! Use NestDB's Edit Mode to add new rows to tables. Make sure to create
            a checkpoint before bulk additions. Follow the existing schema structure.
        </p>

        <h4>Q: How accurate is NestVision?</h4>
        <p>
            <strong>A:</strong> Accuracy varies by image quality and colony density. Typical accuracy is 85-95%
            for well-lit, overhead images of moderate-density colonies. Use Nestperts to verify and improve results.
        </p>

        <h4>Q: Can I train my own detection model?</h4>
        <p>
            <strong>A:</strong> Yes! Use Nestperts to create labeled training data, then train a YOLO model
            using Ultralytics. Replace the ONNX models in the <code>models/</code> directory.
        </p>

        <h4>Q: Is my data secure?</h4>
        <p>
            <strong>A:</strong> NestScope runs locally on your machine. No data is sent to external servers
            except LLM API calls for NestChat (query text and results only). NestVision and NestDB are entirely local.
        </p>

        <h4>Q: Can I export the entire database?</h4>
        <p>
            <strong>A:</strong> Yes! The SQLite database file is at <code>data/bird_data_complete.db</code>.
            You can copy this file or use NestDB's SQL Editor to export specific tables as CSV.
        </p>

        <h4>Q: What species are supported?</h4>
        <p>
            <strong>A:</strong> The database includes 20+ Gulf Coast seabird and wading bird species.
            See Technical Reference tab for full list. Nestperts supports all these species for precise labeling.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Getting Help</h3>

        <h4>Log Files</h4>
        <p>Check these log files for detailed error information:</p>
        <ul>
            <li><code>logs/server.log</code> - FastAPI backend logs</li>
            <li><code>logs/streamlit.log</code> - Frontend logs</li>
            <li><code>logs/nestperts.log</code> - Flask app logs</li>
        </ul>

        <h4>System Status</h4>
        <p>Use the System Status page to check:</p>
        <ul>
            <li>Backend health (API availability)</li>
            <li>Database connection</li>
            <li>Model availability</li>
            <li>Service versions</li>
        </ul>

        <h4>Advanced Debugging</h4>
        <p>For developers:</p>
        <ul>
            <li>FastAPI docs: <code>http://localhost:8000/docs</code></li>
            <li>Test backend: <code>curl http://localhost:8000/health</code></li>
            <li>Check processes: <code>ps aux | grep python</code></li>
            <li>Monitor resources: <code>htop</code> or <code>top</code></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# TAB 7: TECHNICAL REFERENCE
# ============================================================================

with tab7:
    st.markdown("""
        <div class="title-card">
            <h3>Technical Reference</h3>
            <p>
                Detailed technical information about database schema, API endpoints, models, and system architecture.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Database Schema</h3>

        <h4>Primary Tables</h4>

        <h5>tblColonyTotals2010-2021_MayJuneCombined</h5>
        <p><strong>Purpose:</strong> Pre-aggregated bird and nest counts (main data table)</p>
        <p><strong>Key Columns:</strong></p>
        <ul>
            <li><code>Year</code> - Survey year (2010-2021)</li>
            <li><code>Month</code> - Survey month (typically May or June)</li>
            <li><code>State</code> - State abbreviation (TX, LA, MS, AL, FL)</li>
            <li><code>ColonyName</code> - Colony identifier</li>
            <li><code>Latitude</code> - Colony latitude (decimal degrees)</li>
            <li><code>Longitude</code> - Colony longitude (decimal degrees)</li>
            <li><code>Species</code> - Bird species name</li>
            <li><code>Birds</code> - Total bird count</li>
            <li><code>Nests</code> - Total nest count</li>
        </ul>
        <p><strong>Use for:</strong> Population queries, trend analysis, geographic queries</p>

        <h5>tblSpeciesData2010/2011-2013/2015_2018_2021</h5>
        <p><strong>Purpose:</strong> Photo record metadata (NOT for bird counts)</p>
        <p><strong>Key Columns:</strong></p>
        <ul>
            <li><code>PhotoID</code> - Unique photo identifier</li>
            <li><code>Year</code> - Year photo taken</li>
            <li><code>Colony</code> - Colony name</li>
            <li><code>Species</code> - Species photographed</li>
            <li><code>Methodology</code> - Survey method used</li>
        </ul>
        <p><strong>Use for:</strong> Photo methodology questions only</p>

        <h4>Supporting Tables</h4>
        <ul>
            <li><strong>tblColonies:</strong> Colony reference data (names, locations, IDs)</li>
            <li><strong>tblSpecies:</strong> Species reference (scientific names, groups)</li>
            <li><strong>tblSurveyMethods:</strong> Survey methodology descriptions</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Species Reference</h3>

        <h4>Pelicans (Family: Pelecanidae)</h4>
        <ul>
            <li><strong>Brown Pelican</strong> - <em>Pelecanus occidentalis</em></li>
            <li><strong>American White Pelican</strong> - <em>Pelecanus erythrorhynchos</em></li>
        </ul>

        <h4>Cormorants & Anhingas (Family: Phalacrocoracidae, Anhingidae)</h4>
        <ul>
            <li><strong>Double-crested Cormorant</strong> - <em>Phalacrocorax auritus</em></li>
            <li><strong>Neotropic Cormorant</strong> - <em>Phalacrocorax brasilianus</em></li>
            <li><strong>Anhinga</strong> - <em>Anhinga anhinga</em></li>
        </ul>

        <h4>Herons & Egrets (Family: Ardeidae)</h4>
        <ul>
            <li><strong>Great Egret</strong> - <em>Ardea alba</em></li>
            <li><strong>Snowy Egret</strong> - <em>Egretta thula</em></li>
            <li><strong>Reddish Egret</strong> - <em>Egretta rufescens</em></li>
            <li><strong>Cattle Egret</strong> - <em>Bubulcus ibis</em></li>
            <li><strong>Tricolored Heron</strong> - <em>Egretta tricolor</em></li>
            <li><strong>Little Blue Heron</strong> - <em>Egretta caerulea</em></li>
        </ul>

        <h4>Ibises & Spoonbills (Family: Threskiornithidae)</h4>
        <ul>
            <li><strong>White Ibis</strong> - <em>Eudocimus albus</em></li>
            <li><strong>White-faced Ibis</strong> - <em>Plegadis chihi</em></li>
            <li><strong>Roseate Spoonbill</strong> - <em>Platalea ajaja</em></li>
        </ul>

        <h4>Terns (Family: Laridae)</h4>
        <ul>
            <li><strong>Royal Tern</strong> - <em>Thalasseus maximus</em></li>
            <li><strong>Sandwich Tern</strong> - <em>Thalasseus sandvicensis</em></li>
            <li><strong>Least Tern</strong> - <em>Sternula antillarum</em></li>
            <li><strong>Caspian Tern</strong> - <em>Hydroprogne caspia</em></li>
            <li><strong>Forster's Tern</strong> - <em>Sterna forsteri</em></li>
            <li><strong>Common Tern</strong> - <em>Sterna hirundo</em></li>
            <li><strong>Gull-billed Tern</strong> - <em>Gelochelidon nilotica</em></li>
            <li><strong>Black Tern</strong> - <em>Chlidonias niger</em></li>
        </ul>

        <h4>Gulls (Family: Laridae)</h4>
        <ul>
            <li><strong>Laughing Gull</strong> - <em>Leucophaeus atricilla</em></li>
            <li><strong>Ring-billed Gull</strong> - <em>Larus delawarensis</em></li>
            <li><strong>Herring Gull</strong> - <em>Larus argentatus</em></li>
        </ul>

        <h4>Skimmers & Shorebirds</h4>
        <ul>
            <li><strong>Black Skimmer</strong> - <em>Rynchops niger</em> (Family: Laridae)</li>
            <li><strong>American Oystercatcher</strong> - <em>Haematopus palliatus</em> (Family: Haematopodidae)</li>
        </ul>

        <h4>Frigatebirds (Family: Fregatidae)</h4>
        <ul>
            <li><strong>Magnificent Frigatebird</strong> - <em>Fregata magnificens</em></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>API Endpoints</h3>

        <h4>Backend (FastAPI - Port 8000)</h4>

        <h5>Health & Info</h5>
        <ul>
            <li><code>GET /health</code> - Backend health check</li>
            <li><code>GET /config</code> - Get backend configuration (model name, etc.)</li>
            <li><code>GET /</code> - API documentation and endpoint list</li>
        </ul>

        <h5>Database & Schema</h5>
        <ul>
            <li><code>GET /schema</code> - Get complete database schema</li>
            <li><code>GET /tables</code> - List all tables</li>
            <li><code>GET /table/{table_name}/data</code> - Get table data with pagination</li>
            <li><code>GET /table/{table_name}/schema</code> - Get table schema</li>
        </ul>

        <h5>NestChat (Text-to-SQL)</h5>
        <ul>
            <li><code>POST /ask</code> - Submit question, get answer (non-streaming)</li>
            <li><code>POST /ask/stream</code> - Submit question, stream response</li>
        </ul>

        <h5>NestVision (Computer Vision)</h5>
        <ul>
            <li><code>POST /cv/inference</code> - Run bird detection on image</li>
            <li><code>GET /cv/examples</code> - List example images</li>
            <li><code>GET /cv/status</code> - Check CV model status</li>
        </ul>

        <h5>NestDB (Database Management)</h5>
        <ul>
            <li><code>POST /db/update</code> - Update table row</li>
            <li><code>POST /db/delete</code> - Delete table row</li>
            <li><code>POST /db/insert</code> - Insert new row</li>
            <li><code>POST /db/query</code> - Execute custom SQL query</li>
        </ul>

        <h5>Version Control</h5>
        <ul>
            <li><code>GET /version/history</code> - Get commit history</li>
            <li><code>GET /version/diff</code> - Get diff for specific commit</li>
            <li><code>GET /version/stats</code> - Get version control statistics</li>
            <li><code>POST /version/rollback</code> - Rollback to commit</li>
            <li><code>POST /version/checkpoint</code> - Create manual checkpoint</li>
        </ul>

        <h4>Nestperts (Flask - Port 5000)</h4>
        <ul>
            <li><code>GET /</code> - Main annotation interface</li>
            <li><code>POST /api/sam_segment</code> - MobileSAM segmentation</li>
            <li><code>GET /api/sam_status</code> - SAM model status</li>
            <li><code>POST /api/correction/upload</code> - Upload image for correction</li>
            <li><code>GET /nestdb</code> - NestDB interface redirect</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Models & AI</h3>

        <h4>Detection Models (YOLO26)</h4>
        <ul>
            <li><strong>Swift:</strong> <code>models/swift.onnx</code> - Fast inference model</li>
            <li><strong>Apex:</strong> <code>models/apex.onnx</code> - High accuracy model</li>
            <li><strong>Input:</strong> 1024x1024 RGB images</li>
            <li><strong>Output:</strong> Bounding boxes with confidence scores</li>
            <li><strong>Format:</strong> ONNX Runtime optimized</li>
        </ul>

        <h4>Classification Models</h4>
        <ul>
            <li><strong>Swift:</strong> <code>models/classifier_swift.onnx</code></li>
            <li><strong>Apex:</strong> <code>models/classifier_apex.onnx</code></li>
            <li><strong>Input:</strong> 224x224 RGB crops of detected birds</li>
            <li><strong>Output:</strong> 7-class softmax (species groups)</li>
            <li><strong>Classes:</strong> COLOR_WADER, DARK, GULL, PELICAN, SHOREBIRD, TERN, WHITE_WADER</li>
        </ul>

        <h4>Segmentation Model</h4>
        <ul>
            <li><strong>Model:</strong> <code>models/mobile_sam.pt</code> - MobileSAM</li>
            <li><strong>Input:</strong> Point prompts on images</li>
            <li><strong>Output:</strong> Segmentation masks</li>
            <li><strong>Use:</strong> Interactive annotation in Nestperts</li>
        </ul>

        <h4>Language Model (NestChat)</h4>
        <ul>
            <li><strong>Provider:</strong> OpenRouter API</li>
            <li><strong>Default Model:</strong> Configured in <code>server/config.yaml</code></li>
            <li><strong>Purpose:</strong> Text-to-SQL generation and answer synthesis</li>
            <li><strong>Context:</strong> Enhanced metadata with database schema</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>System Architecture</h3>

        <h4>Technology Stack</h4>
        <ul>
            <li><strong>Frontend:</strong> Streamlit (Python web framework)</li>
            <li><strong>Backend:</strong> FastAPI (async Python API framework)</li>
            <li><strong>Database:</strong> SQLite (embedded SQL database)</li>
            <li><strong>CV Framework:</strong> ONNX Runtime (model inference)</li>
            <li><strong>Expert Tool:</strong> Flask (annotation server)</li>
            <li><strong>Version Control:</strong> Git (database versioning)</li>
        </ul>

        <h4>Service Ports</h4>
        <ul>
            <li><strong>8000:</strong> FastAPI backend</li>
            <li><strong>8501:</strong> Streamlit frontend</li>
            <li><strong>5000:</strong> Flask (Nestperts + NestDB)</li>
        </ul>

        <h4>Data Flow</h4>
        <p><strong>NestChat:</strong></p>
        <pre>User Question → Frontend → Backend → LLM API → SQL Generation →
Database Query → Results → LLM Analysis → Frontend Display</pre>

        <p><strong>NestVision:</strong></p>
        <pre>Image Upload → Frontend → Backend → ONNX Inference →
Detection → Classification → Results → Frontend Display</pre>

        <p><strong>NestDB:</strong></p>
        <pre>User Edit → Frontend → Backend → Database Write →
Git Commit → Version History Update</pre>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>File Structure</h3>

        <h4>Key Directories</h4>
        <pre>
nexus/
├── frontend/              # Streamlit app
│   ├── app.py            # Main landing page
│   ├── pages/            # Individual feature pages
│   ├── components/       # Shared UI components
│   ├── services/         # API client functions
│   └── styles/           # CSS and theming
├── server/               # FastAPI backend
│   ├── main.py          # API endpoints
│   ├── prompt.txt       # LLM system prompt
│   └── cv_tools/        # Computer vision code
├── labeller/            # Nestperts Flask app
│   ├── app.py          # Main Flask server
│   ├── templates/      # HTML templates
│   └── nestvision/     # Training data output
├── models/             # ONNX and PyTorch models
│   ├── swift.onnx
│   ├── apex.onnx
│   ├── classifier_swift.onnx
│   ├── classifier_apex.onnx
│   └── mobile_sam.pt
├── data/               # Database and metadata
│   ├── bird_data_complete.db
│   ├── database_metadata_enhanced.json
│   └── .git/          # Version control
├── logs/              # Application logs
│   ├── server.log
│   ├── streamlit.log
│   └── nestperts.log
└── run_app.sh        # Startup script
        </pre>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Configuration Files</h3>

        <h4>server/config.yaml</h4>
        <p>Team-wide configuration (version controlled):</p>
        <ul>
            <li>LLM model selection</li>
            <li>Database paths</li>
            <li>CV model settings</li>
            <li>API configuration</li>
        </ul>

        <h4>.env</h4>
        <p>Local secrets (NOT version controlled):</p>
        <ul>
            <li><code>OPENROUTER_API_KEY</code> - API key for LLM</li>
            <li><code>DB_PATH</code> - Database file location</li>
            <li><code>API_BASE_URL</code> - Backend URL</li>
            <li><code>MODEL_NAME</code> - (Optional) Local model override</li>
        </ul>

        <h4>CLAUDE.md</h4>
        <p>Project documentation for Claude Code:</p>
        <ul>
            <li>Architecture overview</li>
            <li>Development guidelines</li>
            <li>Common patterns</li>
            <li>Troubleshooting tips</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Development Commands</h3>

        <h4>Starting Services</h4>
        <pre>
# All services at once
./run_app.sh

# Individual services
uvicorn server.main:app --reload --port 8000  # Backend
streamlit run frontend/app.py --server.port 8501  # Frontend
python labeller/app.py  # Nestperts
        </pre>

        <h4>Database Operations</h4>
        <pre>
# Migrate Access to SQLite
cd data/
python migrate_access_to_sqlite.py \\
  --input source.accdb \\
  --output bird_data_complete.db

# Direct SQL access
sqlite3 data/bird_data_complete.db
        </pre>

        <h4>Version Control</h4>
        <pre>
# View commit history
cd data/
git log --oneline

# View specific diff
git diff &lt;commit-hash&gt;

# Manual rollback (advanced)
git reset --hard &lt;commit-hash&gt;
        </pre>

        <h4>Log Viewing</h4>
        <pre>
# Tail logs in real-time
tail -f logs/server.log
tail -f logs/streamlit.log
tail -f logs/nestperts.log

# Search logs for errors
grep -i error logs/server.log
        </pre>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="help-section">
        <h3>Performance Metrics</h3>

        <h4>Typical Response Times</h4>
        <ul>
            <li><strong>NestChat:</strong> 2-5 seconds (depends on LLM API)</li>
            <li><strong>NestVision (Swift):</strong> 5-15 seconds per image</li>
            <li><strong>NestVision (Apex):</strong> 15-60 seconds per image</li>
            <li><strong>NestDB Queries:</strong> <1 second for most queries</li>
            <li><strong>Version Control:</strong> 1-3 seconds per commit</li>
        </ul>

        <h4>Resource Requirements</h4>
        <ul>
            <li><strong>RAM:</strong> 4-8 GB recommended</li>
            <li><strong>Disk:</strong> 2-5 GB for app + models</li>
            <li><strong>CPU:</strong> Multi-core recommended for CV</li>
            <li><strong>GPU:</strong> Optional (CUDA support not yet implemented)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

# Footer with version info
st.markdown("""
<div style="
    background: var(--claude-surface);
    border: 1px solid var(--claude-border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 2rem;
    text-align: center;
">
    <p style="color: var(--claude-text-light); margin: 0; font-size: 0.875rem;">
        NestScope v1.0 | Gulf Coast Avian Monitoring Platform
    </p>
    <p style="color: var(--claude-text-light); margin: 0.5rem 0 0 0; font-size: 0.75rem;">
        For additional support, check the system logs or consult the CLAUDE.md file in the project repository.
    </p>
</div>
""", unsafe_allow_html=True)
