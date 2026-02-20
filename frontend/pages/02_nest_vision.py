"""
NestVision Page - Bird Detection & Counting with Computer Vision
"""

import streamlit as st
import pandas as pd
import requests
import base64
from io import BytesIO
from PIL import Image

# Import from modular structure
from services import run_cv_inference, get_example_images, fetch_example_image, API_BASE_URL
from utils import extract_crops_from_detections, load_species_list
from styles import get_custom_css
from components import render_sidebar_header

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="NestVision - NestScope",
    page_icon="🦅",
    layout="wide"
)

# Apply custom CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

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
if "crop_identifications" not in st.session_state:
    st.session_state.crop_identifications = {}

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Render brand header
    render_sidebar_header()

    # Settings Section
    st.markdown("""
        <div style="
            font-size: 0.6875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #A0A0A0;
            margin: 1.5rem 0 0.75rem;
            padding: 0 0.5rem;
            opacity: 0.7;
        ">Settings</div>
    """, unsafe_allow_html=True)

    st.info("💡 **Tip**: Start with Fast Mode for quick previews. Use Zoom Mode for small or distant birds.")

# ============================================================================
# PAGE HEADER
# ============================================================================

st.markdown("""
    <div class="title-card">
        <h3>🦅 NestVision: Bird Detection & Counting</h3>
        <p>
            Powered by AI computer vision, NestVision automatically detects and counts birds in your images.
            Upload a photo or try our example images to see the model in action.
        </p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# MODEL INFORMATION
# ============================================================================

with st.expander("ℹ️ About the Model", expanded=False):
    st.markdown("""
    ### Current Model
    **YOLOv26m-based** bird detection trained on avian monitoring data

    ### Important Notes
    - 🔧 This model is currently in **development** and may not be highly accurate
    - 📊 The team is actively **annotating more training data** to improve performance
    - 🚀 A more **robust model** is being developed with improved accuracy

    ### Processing Modes
    - **⚡ Fast Mode**: Quick inference using downsampling for large images. Best for real-time previews.
    - **🎯 Zoom Mode**: Uses intelligent image slicing with optimal overlap. Better for detecting small or distant birds, but slower.

    ### Future Enhancements
    - 🐦 **Bird species classification** using ImageNet-based models
    - 🎯 Identification of **specific bird species**, not just detection and counting
    - 📈 **Combined detection + classification** will provide complete bird analysis

    ### Technical Details
    - **Input image size**: 1024x1024 pixels
    - **Confidence threshold**: Adjustable (default 0.25)
    - **Model architecture**: YOLO-based object detection (ONNX format)
    - **Smart slicing**: 20% overlap for Zoom mode
    - **Model file**: `server/seconditer.onnx`
    """)

st.markdown("---")

# ============================================================================
# IMAGE UPLOAD SECTION
# ============================================================================

st.markdown("### 📤 Upload Your Image")
uploaded_file = st.file_uploader(
    "Choose an image file containing birds",
    type=['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'],
    help="Upload an image for bird detection and counting",
    key="bird_image_uploader"
)

# ============================================================================
# DETECTION SETTINGS
# ============================================================================

st.markdown("### ⚙️ Detection Settings")
conf_threshold = st.slider(
    "Confidence Threshold",
    min_value=0.1,
    max_value=0.9,
    value=0.25,
    step=0.05,
    help="Lower values detect more birds but may include false positives. Higher values are more selective."
)

# Processing mode selection
st.markdown("**Processing Mode**")
fast_mode = st.radio(
    "Choose detection mode:",
    options=[True, False],
    format_func=lambda x: "⚡ Fast Mode (Recommended)" if x else "🎯 Zoom Mode",
    index=0,
    help="Fast Mode: Quick inference with downsampling, best for previews.\nZoom Mode: Smart slicing with optimal overlap for detecting small or distant birds, but slower.",
    label_visibility="collapsed"
)

st.markdown("---")

# ============================================================================
# EXAMPLE IMAGES GALLERY
# ============================================================================

col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("### 🖼️ Example Images Gallery")
with col2:
    if st.button("🔄 Refresh", help="Reload example images from server"):
        get_example_images.clear()
        st.rerun()

st.caption("Click on an image below to use it for detection")

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
                                f"Detect Birds",
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
    **No example images available yet.**

    To add example images:
    1. Place bird images in `server/cv_tools/images/`
    2. Supported formats: JPG, PNG, BMP, TIFF, WEBP
    3. Images will automatically appear in this gallery

    For now, upload your own image to get started!
    """)

st.markdown("---")

# ============================================================================
# IMAGE PROCESSING & DETECTION
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

# ============================================================================
# DETECTION RESULTS DISPLAY
# ============================================================================

if image_to_process:
    st.markdown("### 🔍 Detection Analysis")

    # Auto-run detection on new image selection or upload
    if auto_run_detection:
        with st.spinner("🔄 Running AI detection..."):
            # Create a file-like object
            image_file = BytesIO(image_to_process)
            image_file.name = image_name

            # Run inference
            result = run_cv_inference(image_file, conf_threshold, fast_mode)

            # Store result in session state
            st.session_state.cv_detection_result = result

    # Get result from session state (whether just computed or previously cached)
    result = st.session_state.cv_detection_result

    if result and "error" not in result:
        # Display original and annotated images side by side
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Original Image")
            original_img = Image.open(BytesIO(image_to_process))
            st.image(original_img, use_container_width=True)

        with col2:
            st.markdown("#### Detected Birds")
            annotated_base64 = result.get("annotated_image_base64", "")
            if annotated_base64:
                annotated_bytes = base64.b64decode(annotated_base64)
                annotated_img = Image.open(BytesIO(annotated_bytes))
                st.image(annotated_img, use_container_width=True)

        # Display results
        bird_count = result.get("bird_count", 0)
        message = result.get("message", "")
        inference_time = result.get("inference_time", 0.0)

        st.markdown("---")
        st.markdown("#### 📊 Results")

        # Show count with appropriate styling
        if bird_count == 0:
            st.warning(message)
            st.info("💡 **Tip**: Try lowering the confidence threshold or use a different image with more visible birds.")
        else:
            st.success(message)

        # Display metrics in columns
        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("🐦 Birds Detected", bird_count)
        with metric_cols[1]:
            original_img = Image.open(BytesIO(image_to_process))
            st.metric("📐 Image Size", f"{original_img.width}×{original_img.height}")
        with metric_cols[2]:
            st.metric("🎯 Confidence", f"{conf_threshold:.0%}")
        with metric_cols[3]:
            st.metric("⚡ Inference Time", f"{inference_time:.2f}s")

        # ====================================================================
        # DOWNLOAD AND CORRECTION WORKFLOW
        # ====================================================================

        if annotated_base64:
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 Download Annotated Image",
                    data=annotated_bytes,
                    file_name=f"nestvision_detected_{image_name}",
                    mime="image/jpeg",
                    use_container_width=True,
                    type="secondary"
                )
            with col2:
                if st.button("🔧 Correct AI", use_container_width=True, type="primary"):
                    # Send image and detections to labeller
                    with st.spinner("Uploading to labeller..."):
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

                                # Auto-open labeller in new tab using JavaScript
                                st.success(f"✅ Uploaded as {image_filename}! Opening labeller...")

                                # JavaScript to open in new window
                                js_code = f"""
                                <script>
                                    window.open('{correction_url}', '_blank');
                                </script>
                                """
                                st.components.v1.html(js_code, height=0)

                                # Also provide a fallback link
                                st.markdown(f"**If the page didn't open automatically:** [Click here to open labeller]({correction_url})")
                                st.info("💡 Your image has been added to the 'Corrections' user in the labeller. Use all the labelling tools to fix the detections!")
                            else:
                                st.error(f"Failed to upload: {correction_response.status_code}")
                        except Exception as e:
                            st.error(f"Error: Make sure the labeller app is running on port 5000")
                            st.code(f"python labeller/app.py --data nestvision")

        # ====================================================================
        # DETECTION DETAILS
        # ====================================================================

        if bird_count > 0:
            with st.expander("🔍 View Detailed Detection Data", expanded=False):
                detections = result.get("detections", [])
                if detections:
                    st.markdown(f"**Total Detections:** {len(detections)}")
                    st.markdown("**Detection Details:**")

                    # Create a formatted table
                    detection_data = []
                    for i, det in enumerate(detections, 1):
                        bbox = det.get('bbox', [])
                        detection_data.append({
                            "Detection #": i,
                            "Confidence": f"{det.get('confidence', 0):.2%}",
                            "Bounding Box": f"[{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]",
                            "Class ID": det.get('class_id', 0)
                        })

                    st.dataframe(pd.DataFrame(detection_data), use_container_width=True)

                    # Raw JSON data
                    with st.expander("📄 Raw JSON Data"):
                        st.json({
                            "total_detections": len(detections),
                            "detections": detections
                        })

        # ====================================================================
        # SPECIES IDENTIFICATION SECTION
        # ====================================================================

        if bird_count > 0:
            st.markdown("---")
            st.markdown("### 🐦 Species Identification Training")
            st.caption("Help improve species recognition by identifying birds in these crops")

            # Extract random crops
            detections = result.get("detections", [])
            crops = extract_crops_from_detections(image_to_process, detections, num_crops=5)

            if crops:
                # Load species list
                species_list = load_species_list()
                species_options = ["Not a bird"] + [f"{code} - {name}" for code, name in species_list]

                # Display crops in a grid
                num_cols = min(5, len(crops))
                cols = st.columns(num_cols)

                for idx, (crop_bytes, det) in enumerate(crops):
                    with cols[idx % num_cols]:
                        # Display crop
                        crop_img = Image.open(BytesIO(crop_bytes))
                        st.image(crop_img, use_container_width=True, caption=f"Detection #{idx+1}")

                        # Species selector
                        crop_key = f"crop_{id(image_name)}_{idx}"
                        selected_species = st.selectbox(
                            "Species",
                            options=species_options,
                            key=f"species_select_{crop_key}",
                            label_visibility="collapsed"
                        )

                        # Save button
                        if st.button("💾 Save", key=f"save_crop_{crop_key}", use_container_width=True):
                            if selected_species == "Not a bird":
                                st.warning("Please select a species")
                            else:
                                # Extract species code
                                species_code = selected_species.split(" - ")[0]
                                species_name = selected_species.split(" - ")[-1]

                                # Send to backend
                                with st.spinner("Saving crop..."):
                                    try:
                                        crop_data = {
                                            "crop_base64": base64.b64encode(crop_bytes).decode('utf-8'),
                                            "species_code": species_code,
                                            "species_name": species_name
                                        }

                                        crop_response = requests.post(
                                            "http://localhost:5000/api/crop/save",
                                            json=crop_data,
                                            timeout=30
                                        )

                                        if crop_response.status_code == 200:
                                            st.success(f"✅ Saved as {species_code}!")
                                            st.session_state.crop_identifications[crop_key] = species_code
                                        else:
                                            st.error("Failed to save crop")
                                    except Exception as e:
                                        st.error("Error: Make sure labeller app is running")
                                        st.code("python labeller/app.py")

                st.markdown("---")
                st.info("""
                **Why identify species?**

                These identified crops will be used to train a species classification model.
                The more accurate identifications we collect, the better the model becomes!

                Crops are saved to: `nestvision/crops/`
                """)

    elif result and "error" in result:
        st.error(f"❌ Inference failed: {result['error']}")
else:
    # Show instructions when no image is selected
    st.info("""
    ### 👆 Get Started

    **To detect birds in an image:**
    1. **Upload** your own image using the file uploader above, or
    2. **Select** an example image from the gallery above
    3. Adjust the **confidence threshold** if needed
    4. Click **"Run Bird Detection"** to analyze the image

    The AI will identify and count all birds in your image!
    """)
