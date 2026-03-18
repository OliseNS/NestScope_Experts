"""
NestVision Page - Bird Detection & Counting with Computer Vision
"""

import streamlit as st
import pandas as pd
import requests
import base64
from io import BytesIO
from PIL import Image
import plotly.express as px

# Import from modular structure
from services import run_cv_inference, get_example_images, fetch_example_image, API_BASE_URL
from utils import load_species_list
from components import init_page, render_header, render_sidebar

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

# Initialize page with shared layout
init_page(page_title="NestVision - NestScope", page_icon="🦅", layout="wide")

# Render shared header
render_header(page_name="NestVision")

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

# Initialize session state for selected example
if "selected_example_image" not in st.session_state:
    st.session_state.selected_example_image = None
if "selected_example_name" not in st.session_state:
    st.session_state.selected_example_name = None
if "cv_detection_result" not in st.session_state:
    st.session_state.cv_detection_result = None
if "cv_last_processed_image" not in st.session_state:
    st.session_state.cv_last_processed_image = None
if "cv_conf_threshold" not in st.session_state:
    st.session_state.cv_conf_threshold = 0.25

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Render shared navigation, tools, and status
    render_sidebar(active_page="nestvision")

# ============================================================================
# PAGE HEADER
# ============================================================================

st.markdown("""
    <div class="title-card">
        <h3>🦅 NestVision: Bird Detection & Counting</h3>
        <p>
            Upload an image or select an example to automatically detect and count birds using AI.
            Species classification shows the model's best prediction for each bird.
        </p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# 1. IMAGE SELECTION (Primary Action)
# ============================================================================

st.markdown("## 📤 Select Image")

# Upload section
uploaded_file = st.file_uploader(
    "Upload your own image",
    type=['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'],
    help="Choose an image containing birds for automatic detection",
    key="bird_image_uploader"
)

st.markdown("### Or Choose Example Image")

# Example images gallery
col_refresh_1, col_refresh_2 = st.columns([5, 1])
with col_refresh_2:
    if st.button("🔄 Refresh", help="Reload example images"):
        get_example_images.clear()
        st.rerun()

example_images = get_example_images()

if example_images:
    # Display gallery in a grid
    cols_per_row = 4
    num_rows = (len(example_images) + cols_per_row - 1) // cols_per_row

    for row in range(num_rows):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            img_idx = row * cols_per_row + col_idx
            if img_idx < len(example_images):
                with cols[col_idx]:
                    example_name = example_images[img_idx]
                    try:
                        # Fetch and display thumbnail (cached)
                        image_bytes = fetch_example_image(example_name)
                        if image_bytes:
                            img = Image.open(BytesIO(image_bytes))
                            st.image(img, use_container_width=True)

                            # Button to select this image
                            if st.button(
                                f"Use This Image",
                                key=f"use_example_{img_idx}",
                                use_container_width=True,
                                type="primary"
                            ):
                                st.session_state.selected_example_image = image_bytes
                                st.session_state.selected_example_name = example_name
                                st.session_state.cv_detection_result = None
                                st.session_state.cv_last_processed_image = None
                                st.rerun()

                            st.caption(example_name)
                    except Exception as e:
                        st.error(f"Error loading {example_name}")
else:
    st.info("""
    **No example images available.**

    To add examples, place bird images in `server/cv_tools/images/`

    For now, upload your own image above!
    """)

# ============================================================================
# 2. DETECTION SETTINGS (Advanced - Collapsed by Default)
# ============================================================================

with st.expander("⚙️ Advanced Settings", expanded=False):
    st.markdown("### Detection Configuration")

    st.markdown("**Detection Confidence**")
    conf_threshold = st.slider(
        "Minimum confidence threshold",
        min_value=0.1,
        max_value=0.9,
        value=st.session_state.cv_conf_threshold,
        step=0.05,
        help="Lower values detect more birds but may include false positives",
        key="conf_slider"
    )
    st.session_state.cv_conf_threshold = conf_threshold

    st.markdown("---")
    st.markdown("""
    **About the Models:**
    - **Detection**: Swift YOLO26 trained on Gulf Coast avian data
    - **Classification**: Swift classifier for 7 species groups
    - **SAHI Processing**: Automatically slices large images for better accuracy
    - **Confidence Thresholds**:
        - Detection: Adjustable (default 25%)
        - Classification: Shows best guess for species group
    """)

# ============================================================================
# 3. DETECTION & RESULTS
# ============================================================================

# Determine which image to process
image_to_process = None
image_name = None
auto_run_detection = False

if uploaded_file is not None:
    image_to_process = uploaded_file.getvalue()
    image_name = uploaded_file.name
    # Check if this is a new upload
    if st.session_state.cv_last_processed_image != image_name:
        auto_run_detection = True
        st.session_state.cv_last_processed_image = image_name
        st.session_state.cv_detection_result = None
elif st.session_state.selected_example_image is not None:
    image_to_process = st.session_state.selected_example_image
    image_name = st.session_state.selected_example_name
    # Check if this is a new selection
    if st.session_state.cv_last_processed_image != image_name:
        auto_run_detection = True
        st.session_state.cv_last_processed_image = image_name
        st.session_state.cv_detection_result = None

# Process image if selected
if image_to_process:
    st.markdown("---")
    st.markdown("## 🔍 Detection Results")

    # Auto-run detection on new image
    if auto_run_detection:
        with st.spinner("🔄 Running AI detection... This may take a few seconds."):
            # Create a file-like object
            image_file = BytesIO(image_to_process)
            image_file.name = image_name

            # Run inference with current settings (Swift mode)
            result = run_cv_inference(
                image_file,
                st.session_state.cv_conf_threshold
            )

            # Store result in session state
            st.session_state.cv_detection_result = result

    # Get result from session state
    result = st.session_state.cv_detection_result

    if result and "error" not in result:
        # Get detection data
        bird_count = result.get("bird_count", 0)
        species_summary = result.get("species_summary", {})
        display_summary = {k: v for k, v in species_summary.items() if k != "UNKNOWN"} or species_summary
        annotated_base64 = result.get("annotated_image_base64", "")
        inference_time = result.get("inference_time", 0.0)

        # Build species code to name mapping
        detections = result.get("detections", [])
        species_names = {}
        for det in detections:
            code = det.get("species_code", "")
            name = det.get("species_name", "")
            if code and code not in species_names:
                species_names[code] = name

        # ====================================================================
        # DISPLAY: Annotated Image with Watermark
        # ====================================================================

        if annotated_base64:
            from PIL import ImageDraw, ImageFont

            annotated_bytes = base64.b64decode(annotated_base64)
            annotated_img = Image.open(BytesIO(annotated_bytes))

            # Add watermark to bottom-right corner
            draw = ImageDraw.Draw(annotated_img)

            # Try to load a nice font for watermark
            try:
                watermark_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            except:
                try:
                    watermark_font = ImageFont.truetype("arial.ttf", 48)
                except:
                    watermark_font = ImageFont.load_default()

            # Watermark text
            watermark_text = "NestVision"

            # Get text size for positioning
            bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Position at bottom-right with padding
            padding = 20
            x = annotated_img.width - text_width - padding
            y = annotated_img.height - text_height - padding

            # Draw semi-transparent background rectangle
            bg_padding = 10
            draw.rectangle(
                [x - bg_padding, y - bg_padding, x + text_width + bg_padding, y + text_height + bg_padding],
                fill=(0, 0, 0, 180)
            )

            # Draw watermark text (orange brand color)
            draw.text((x, y), watermark_text, fill=(217, 119, 87), font=watermark_font)

            # Display the watermarked image
            st.image(annotated_img, use_container_width=True)

        # ====================================================================
        # DISPLAY: Summary Metrics
        # ====================================================================

        st.markdown("### 📊 Summary")

        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("🐦 Total Birds", bird_count)
        with metric_cols[1]:
            st.metric("🎯 Confidence", f"{st.session_state.cv_conf_threshold:.0%}")
        with metric_cols[2]:
            st.metric("⏱️ Time", f"{inference_time:.2f}s")

        # Show message
        if bird_count == 0:
            st.warning("No birds detected. Try lowering the confidence threshold or using a different image.")
        else:
            st.success(result.get("message", f"Detected {bird_count} birds"))

        # ====================================================================
        # DISPLAY: Species Breakdown
        # ====================================================================

        if display_summary and bird_count > 0:
            st.markdown("---")
            st.markdown("### 🦜 Species Breakdown (Best Predictions)")

            # Metric tiles per species (top 5)
            top_species = sorted(display_summary.items(), key=lambda x: -x[1])[:5]
            species_cols = st.columns(len(top_species))

            for i, (species_code, count) in enumerate(top_species):
                with species_cols[i]:
                    species_name = species_names.get(species_code, species_code)
                    st.metric(
                        label=species_code,
                        value=count,
                        help=species_name
                    )

            # Horizontal bar chart
            if len(display_summary) > 1:
                # Build labels with species codes and names
                chart_labels = []
                for code in display_summary.keys():
                    name = species_names.get(code, code)
                    if name and name != code:
                        chart_labels.append(f"{code} - {name}")
                    else:
                        chart_labels.append(code)

                fig = px.bar(
                    x=list(display_summary.values()),
                    y=chart_labels,
                    orientation="h",
                    color_discrete_sequence=["#D97757"],
                    labels={"x": "Count", "y": "Species"},
                    template="plotly_dark",
                )
                fig.update_layout(
                    paper_bgcolor="#1A1A1A",
                    plot_bgcolor="#2D2D2D",
                    showlegend=False,
                    height=max(150, len(display_summary) * 40),
                    margin=dict(l=10, r=10, t=10, b=10),
                    yaxis=dict(categoryorder="total ascending")
                )
                st.plotly_chart(fig, use_container_width=True)

        # ====================================================================
        # DISPLAY: Action Buttons
        # ====================================================================

        st.markdown("---")
        st.markdown("### 💾 Export & Training")

        col1, col2 = st.columns(2)

        with col1:
            if annotated_base64:
                st.download_button(
                    label="📥 Download Annotated Image",
                    data=annotated_bytes,
                    file_name=f"nestvision_{image_name}",
                    mime="image/jpeg",
                    use_container_width=True,
                    type="secondary"
                )

        with col2:
            if st.button("🧑‍🔬 Train with Experts", use_container_width=True, type="primary", help="Send to Nestperts for expert annotation"):
                # Send image and detections to Nestperts
                with st.spinner("Uploading to Nestperts..."):
                    correction_data = {
                        "image_base64": base64.b64encode(image_to_process).decode('utf-8'),
                        "detections": result.get("detections", [])
                    }

                    try:
                        correction_response = requests.post(
                            "http://localhost:5000/api/correction/upload",
                            json=correction_data,
                            timeout=30
                        )

                        if correction_response.status_code == 200:
                            correction_result = correction_response.json()
                            correction_url = f"http://localhost:5000{correction_result['correction_url']}"
                            image_filename = correction_result.get('image_filename', '')

                            st.success(f"✅ Uploaded as {image_filename}!")
                            st.info(f"💡 **Next Step:** Open Nestperts to refine detections and identify species.\n\n[Open Nestperts →]({correction_url})")
                        else:
                            st.error(f"Failed to upload: {correction_response.status_code}")
                            st.info("Make sure Nestperts is running: `python labeller/app.py --data labeller/nestvision`")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")
                        st.info("Make sure Nestperts is running on port 5000:\n\n`python labeller/app.py --data labeller/nestvision`")

        # ====================================================================
        # DISPLAY: Expandable Details
        # ====================================================================

        with st.expander("📷 View Original Image", expanded=False):
            original_img = Image.open(BytesIO(image_to_process))
            st.image(original_img, use_container_width=True)

            # Image info
            st.caption(f"**Size:** {original_img.width}×{original_img.height} pixels")
            st.caption(f"**Format:** {original_img.format}")

        if bird_count > 0:
            with st.expander("🔍 Detection Details", expanded=False):
                detections = result.get("detections", [])
                if detections:
                    # Create formatted table
                    detection_data = []
                    for i, det in enumerate(detections, 1):
                        species_code = det.get('species_code', '')
                        species_name = det.get('species_name', '')
                        det_conf = det.get('confidence', 0)
                        cls_conf = det.get('species_confidence', 0.0)

                        detection_data.append({
                            "#": i,
                            "Species": f"{species_code}" if species_code != 'UNKNOWN' else "—",
                            "Common Name": species_name if species_name != 'Unknown' else "—",
                            "Detection": f"{det_conf:.0%}",
                            "Classification": f"{cls_conf:.0%}" if cls_conf else "—",
                        })

                    df = pd.DataFrame(detection_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # Raw JSON
                    with st.expander("📄 Raw JSON"):
                        st.json({
                            "total_detections": len(detections),
                            "detections": detections
                        })

        with st.expander("ℹ️ About NestVision", expanded=False):
            st.markdown("""
            ### Detection Model
            - **Swift YOLO26**: Fast, accurate bird detection trained on Gulf Coast avian data
            - Optimized for speed and precision
            - Input resolution: 1024×1024 pixels

            ### Species Classification
            - **7 color-coded species groups**: Pelican, Tern, Gull, Shorebird, Cormorant, Heron, Wader
            - **Best prediction shown**: Model's top guess for each bird
            - Use **Nestperts** to verify and refine species identifications
            - Species shown as **4-letter codes** (e.g., BRPE = Brown Pelican)

            ### Understanding Confidence
            - **Detection confidence (70-80%)**: How sure the model is there's a bird
            - **Classification confidence**: Which species group is most likely
            - Higher confidence = more certain identification

            ### SAHI Processing
            - Automatically slices large images into overlapping tiles
            - 20% overlap ensures no birds are missed at tile boundaries
            - Intelligent merging removes duplicate detections

            ### Technical Details
            - **Detection Model**: Swift YOLO26 (1024×1024 input)
            - **Classification Model**: Swift ResNet-based (224×224 input)
            - **NMS Threshold**: 50% IoU
            - **Training Data**: Gulf Coast avian monitoring 2010-2021
            """)

    elif result and "error" in result:
        st.error(f"❌ Detection failed: {result['error']}")
        st.info("Try a different image or adjust the settings.")

else:
    # No image selected - show instructions
    st.markdown("---")
    st.info("""
    ### 👆 Get Started

    **To detect and count birds:**
    1. **Upload** your own image, or
    2. **Select** an example image from the gallery
    3. Detection will run automatically!

    **Optional:** Adjust detection settings in the "Advanced Settings" panel above.
    """)
