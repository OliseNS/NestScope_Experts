"""
Species ID - Gulf Coast Waterbird Visual Guide
Interactive species identification gallery with Wikimedia reference images
"""

import streamlit as st
import requests
from components import init_page, render_header, render_sidebar
from services import API_BASE_URL

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

init_page(page_title="Species ID - NestScope", page_icon="🐦", layout="wide")
render_header(page_name="Species ID")

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    render_sidebar(active_page="speciesid")

    st.markdown("---")
    st.markdown("### 🔍 Filters")

    # Search box
    search_query = st.text_input(
        "Search species",
        placeholder="e.g., LAGU, Laughing, Pelican",
        help="Search by code or name"
    )

    # Sort options
    sort_by = st.radio(
        "Sort by",
        ["Alphabetical", "Code"],
        help="Choose sorting order"
    )

# ============================================================================
# PAGE HEADER
# ============================================================================

st.markdown("""
    <div class="title-card">
        <h3>🐦 Species ID: Gulf Coast Waterbirds</h3>
        <p>
            Visual reference guide for all 73 species in our database.
            Browse reference images from Wikimedia Commons and learn species characteristics.
        </p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# LOAD SPECIES DATA
# ============================================================================

@st.cache_data(ttl=600)
def get_all_species():
    """Fetch all species from backend"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/species", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error loading species: {e}")
        return []

@st.cache_data(ttl=3600)
def get_species_images(species_name, max_images=3, offset=0):
    """Fetch Wikimedia images for a species"""
    try:
        # Use the Nestperts endpoint (it has the Wikipedia integration)
        response = requests.get(
            f"http://localhost:5000/api/species/images/{species_name}",
            params={"max": max_images, "offset": offset},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        return data.get("images", []), data.get("has_more", False)
    except Exception as e:
        return [], False

# Load all species
all_species = get_all_species()

# Filter species based on search
if search_query:
    query_lower = search_query.lower()
    filtered_species = [
        s for s in all_species
        if query_lower in s['code'].lower() or query_lower in s['name'].lower()
    ]
else:
    filtered_species = all_species

# Sort species
if sort_by == "Alphabetical":
    filtered_species = sorted(filtered_species, key=lambda x: x['name'])
else:  # Code
    filtered_species = sorted(filtered_species, key=lambda x: x['code'])

# ============================================================================
# DISPLAY SPECIES GRID
# ============================================================================

st.markdown(f"### Found {len(filtered_species)} species")

if len(filtered_species) == 0:
    st.warning(f"No species found matching '{search_query}'")
else:
    # Session state for tracking expanded species
    if "expanded_species" not in st.session_state:
        st.session_state.expanded_species = set()
    if "species_image_offsets" not in st.session_state:
        st.session_state.species_image_offsets = {}

    # Display species in a clean list
    for species in filtered_species:
        species_code = species['code']
        species_name = species['name']

        # Create expandable container
        with st.expander(f"**{species_code}** — {species_name}", expanded=species_code in st.session_state.expanded_species):
            # When expanded, load images
            col_info, col_images = st.columns([1, 2])

            with col_info:
                st.markdown(f"### {species_name}")
                st.markdown(f"**Code:** `{species_code}`")
                st.markdown("**Source:** Database records 2010-2021")

                # Toggle expansion state
                if st.button(f"Collapse", key=f"collapse_{species_code}"):
                    st.session_state.expanded_species.discard(species_code)
                    st.rerun()

            with col_images:
                # Get current offset for this species
                offset = st.session_state.species_image_offsets.get(species_code, 0)

                # Load images
                with st.spinner("Loading reference images from Wikimedia Commons..."):
                    images, has_more = get_species_images(species_name, max_images=3, offset=offset)

                if images:
                    # Display images in columns
                    img_cols = st.columns(3)
                    for idx, img_url in enumerate(images):
                        with img_cols[idx]:
                            try:
                                st.image(img_url, use_container_width=True, caption=f"Image {offset + idx + 1}")
                            except Exception as e:
                                st.error(f"Failed to load image")

                    # Load More button
                    button_cols = st.columns([1, 1, 2])
                    with button_cols[0]:
                        if offset > 0:
                            if st.button("← Previous", key=f"prev_{species_code}"):
                                st.session_state.species_image_offsets[species_code] = max(0, offset - 3)
                                st.rerun()
                    with button_cols[1]:
                        if has_more:
                            if st.button("Next →", key=f"next_{species_code}"):
                                st.session_state.species_image_offsets[species_code] = offset + 3
                                st.rerun()

                    st.caption(f"Showing images {offset + 1}-{offset + len(images)} • Source: Wikimedia Commons")
                else:
                    st.info(f"No reference images found for {species_name} on Wikimedia Commons.")
                    st.caption("This species may have limited photographic documentation or use an alternate naming convention.")

            # Mark as expanded
            st.session_state.expanded_species.add(species_code)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#555; font-size:0.8rem; padding:0.5rem">
    <strong>Species ID</strong> — Reference images sourced from Wikimedia Commons under Creative Commons licenses.
    Used for educational identification purposes.
</div>
""", unsafe_allow_html=True)
