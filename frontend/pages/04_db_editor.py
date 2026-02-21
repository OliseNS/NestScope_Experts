"""
NestDB Page - Database Management Interface
Supabase-like interface for viewing, editing, and managing database tables
"""

import streamlit as st
import pandas as pd

# Import from modular structure
from services import (
    get_tables,
    get_table_data,
    get_table_schema,
    update_table_row,
    delete_table_row,
    insert_table_row
)
from components import render_sidebar_section, render_service_status_link
from styles import get_custom_css

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="NestDB - NestScope",
    page_icon="🗄️",
    layout="wide"
)

# Apply custom CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Hide Streamlit's default page navigation and add fixed header
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: #1E1E1E;
        border-bottom: 1px solid #333;
        padding: 0.75rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        z-index: 999999;
    }
    .main-content {
        margin-top: 4rem;
    }
</style>
""", unsafe_allow_html=True)

# Fixed header
st.markdown("""
    <div class="fixed-header">
        <span style="font-size: 1.5rem;">🦅</span>
        <span style="font-size: 1rem; font-weight: 600; color: #E5E5E5;">NestScope</span>
        <span style="color: #666; font-size: 0.875rem;">Avian Monitoring Suite</span>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "db_selected_table" not in st.session_state:
    st.session_state.db_selected_table = None

if "db_current_page" not in st.session_state:
    st.session_state.db_current_page = 1

if "db_page_size" not in st.session_state:
    st.session_state.db_page_size = 50

if "db_editing_mode" not in st.session_state:
    st.session_state.db_editing_mode = False

if "db_edited_data" not in st.session_state:
    st.session_state.db_edited_data = None

if "db_show_add_row" not in st.session_state:
    st.session_state.db_show_add_row = False

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Navigation Section
    render_sidebar_section("Navigation")

    if st.button("🏠 Home", use_container_width=True, help="Return to home page"):
        st.switch_page("app.py")

    if st.button("💬 NestChat", use_container_width=True, help="Natural language data queries"):
        st.switch_page("pages/01_nest_chat.py")

    if st.button("🦅 NestVision", use_container_width=True, help="AI bird detection & counting"):
        st.switch_page("pages/02_nest_vision.py")

    if st.button("🗄️ NestDB", use_container_width=True, help="Database management interface", type="primary"):
        st.rerun()

    # Tools section
    render_sidebar_section("Tools")

    st.link_button("🧑‍🔬 Nestperts", "http://localhost:5000", use_container_width=True, help="Expert species training platform")

    # System Status section
    render_sidebar_section("System Status")
    render_service_status_link()

# ============================================================================
# MAIN INTERFACE
# ============================================================================

st.title("NestDB")
st.caption("Database management interface - view, edit, and add data")

# Create tabs for Table Browser and Schema Viewer
tab1, tab2 = st.tabs(["📊 Table Browser", "📋 Schema Viewer"])

# ============================================================================
# TAB 1: TABLE BROWSER
# ============================================================================

with tab1:
    # Welcome Card
    st.markdown("""
        <div class="title-card">
            <h3>Database Table Manager</h3>
            <p>
                Select a table to view and edit its data. Toggle Edit Mode to modify values or add new rows.
                View table schemas in the Schema Viewer tab for detailed column information.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Fetch table list
    tables_response = get_tables()

    if "error" in tables_response:
        st.error(f"Failed to fetch tables: {tables_response['error']}")
        st.stop()

    tables = tables_response.get("tables", [])

    if not tables:
        st.warning("No tables found in the database.")
        st.stop()

    # Table selection
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        selected_table = st.selectbox(
            "Select Table",
            options=tables,
            index=tables.index(st.session_state.db_selected_table) if st.session_state.db_selected_table in tables else 0,
            key="table_selector"
        )

    with col2:
        page_size = st.selectbox(
            "Rows per page",
            options=[25, 50, 100, 200],
            index=1,
            key="page_size_selector"
        )

    with col3:
        edit_mode = st.toggle("Edit Mode", value=st.session_state.db_editing_mode, help="Enable editing of table data")

    # Update session state if table or page size changed
    if selected_table != st.session_state.db_selected_table:
        st.session_state.db_selected_table = selected_table
        st.session_state.db_current_page = 1  # Reset to page 1 when changing tables
        st.session_state.db_edited_data = None  # Clear edited data

    if page_size != st.session_state.db_page_size:
        st.session_state.db_page_size = page_size
        st.session_state.db_current_page = 1  # Reset to page 1 when changing page size
        st.session_state.db_edited_data = None  # Clear edited data

    if edit_mode != st.session_state.db_editing_mode:
        st.session_state.db_editing_mode = edit_mode
        st.session_state.db_edited_data = None  # Clear edited data when toggling mode

    # Fetch table data and schema
    with st.spinner(f"Loading data from {selected_table}..."):
        data_response = get_table_data(
            selected_table,
            page=st.session_state.db_current_page,
            page_size=st.session_state.db_page_size
        )

        # Also fetch schema to identify primary keys
        schema_response = get_table_schema(selected_table)

    if not data_response.get("success"):
        st.error(f"Failed to load table data: {data_response.get('error', 'Unknown error')}")
        st.stop()

    if not schema_response.get("success"):
        st.error(f"Failed to load table schema: {schema_response.get('error', 'Unknown error')}")
        st.stop()

    # Extract data and schema
    data = data_response.get("data", [])
    total_rows = data_response.get("total_rows", 0)
    total_pages = data_response.get("total_pages", 0)
    current_page = data_response.get("page", 1)
    schema_columns = schema_response.get("columns", [])

    # Identify primary key columns
    pk_columns = [col['name'] for col in schema_columns if col['pk']]

    # Display table info
    edit_mode_indicator = "✏️ Edit Mode" if st.session_state.db_editing_mode else "👁️ View Mode"
    st.markdown(f"""
    <div style="background: var(--claude-surface); border: 1px solid var(--claude-border); border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
        <strong style="color: var(--claude-orange);">{selected_table}</strong>
        <span style="color: var(--claude-text-light); margin-left: 1rem;">
            {total_rows:,} total rows | Page {current_page} of {total_pages} | {edit_mode_indicator}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Add New Row section (only in edit mode)
    if st.session_state.db_editing_mode and pk_columns:
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("➕ Add New Row", use_container_width=True, type="secondary"):
                st.session_state.db_show_add_row = not st.session_state.db_show_add_row

        if st.session_state.db_show_add_row:
            with st.expander("➕ Add New Row", expanded=True):
                st.markdown("Fill in the values for the new row:")

                new_row_data = {}

                # Create form for new row
                with st.form(key=f"add_row_form_{selected_table}"):
                    # Create input fields for each column
                    for col_info in schema_columns:
                        col_name = col_info['name']
                        col_type = col_info['type']
                        is_required = col_info['notnull']
                        default_val = col_info['default_value']

                        # Determine input type based on column type
                        if 'INT' in col_type.upper():
                            if col_info['pk']:
                                # For primary keys, show as text but make it clear it's auto-generated or required
                                st.text_input(
                                    f"{col_name} ({col_type}) 🔑",
                                    value="" if default_val is None else str(default_val),
                                    help="Primary key - leave empty for auto-increment" if not is_required else "Primary key - required",
                                    key=f"new_row_{col_name}"
                                )
                            else:
                                st.number_input(
                                    f"{col_name} ({col_type}){'*' if is_required else ''}",
                                    value=int(default_val) if default_val is not None else 0,
                                    step=1,
                                    help="Required field" if is_required else "Optional field",
                                    key=f"new_row_{col_name}"
                                )
                        elif 'REAL' in col_type.upper() or 'FLOAT' in col_type.upper() or 'DOUBLE' in col_type.upper():
                            st.number_input(
                                f"{col_name} ({col_type}){'*' if is_required else ''}",
                                value=float(default_val) if default_val is not None else 0.0,
                                step=0.1,
                                format="%.2f",
                                help="Required field" if is_required else "Optional field",
                                key=f"new_row_{col_name}"
                            )
                        else:
                            st.text_input(
                                f"{col_name} ({col_type}){'*' if is_required else ''}",
                                value="" if default_val is None else str(default_val),
                                help="Required field" if is_required else "Optional field",
                                key=f"new_row_{col_name}"
                            )

                    # Submit button
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        submit = st.form_submit_button("💾 Insert Row", use_container_width=True, type="primary")

                    if submit:
                        # Collect all values
                        for col_info in schema_columns:
                            col_name = col_info['name']
                            value = st.session_state.get(f"new_row_{col_name}")

                            # Skip empty primary keys (for auto-increment)
                            if col_info['pk'] and (value == "" or value is None):
                                continue

                            # Skip empty non-required fields
                            if not col_info['notnull'] and (value == "" or value is None):
                                continue

                            new_row_data[col_name] = value

                        # Insert the row
                        if new_row_data:
                            response = insert_table_row(selected_table, new_row_data)

                            if response.get("success"):
                                st.success(f"✅ {response.get('message', 'Row inserted successfully')}")
                                st.session_state.db_show_add_row = False
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to insert row: {response.get('error', 'Unknown error')}")
                        else:
                            st.warning("Please fill in at least one field.")

        st.markdown("---")

    # Display data
    if not data:
        st.info("This table is empty.")
    else:
        df = pd.DataFrame(data)

        # Store original data for comparison
        if "db_original_data" not in st.session_state or st.session_state.db_original_data is None:
            st.session_state.db_original_data = df.copy()

        # Display dataframe - use data_editor in edit mode, regular dataframe otherwise
        if st.session_state.db_editing_mode:
            # Editable dataframe
            st.info("💡 **Tip:** Click on any cell to edit its value. Click 'Save Changes' when done.")

            edited_df = st.data_editor(
                df,
                use_container_width=True,
                height=500,
                hide_index=True,
                disabled=pk_columns,  # Disable editing of primary key columns
                key=f"data_editor_{selected_table}_{current_page}"
            )

            # Check if data was modified
            data_changed = not edited_df.equals(st.session_state.db_original_data)

            if data_changed:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("💾 Save Changes", type="primary", use_container_width=True):
                        # Find changed rows
                        changes_saved = 0
                        errors = []

                        for idx, (original_row, edited_row) in enumerate(zip(st.session_state.db_original_data.to_dict('records'), edited_df.to_dict('records'))):
                            # Check if this row changed
                            if original_row != edited_row:
                                # Build row_id from primary keys
                                row_id = {}
                                if not pk_columns:
                                    # If no primary key, use all original columns as identifier
                                    row_id = original_row
                                else:
                                    for pk_col in pk_columns:
                                        row_id[pk_col] = original_row[pk_col]

                                # Build updates dict (only changed columns)
                                updates = {}
                                for col in edited_df.columns:
                                    if col not in pk_columns and original_row[col] != edited_row[col]:
                                        updates[col] = edited_row[col]

                                if updates:
                                    # Send update to backend
                                    response = update_table_row(selected_table, row_id, updates)

                                    if response.get("success"):
                                        changes_saved += 1
                                    else:
                                        errors.append(f"Row {idx + 1}: {response.get('error', 'Unknown error')}")

                        # Show results
                        if changes_saved > 0:
                            st.success(f"✅ Successfully saved {changes_saved} row(s)")
                            st.session_state.db_original_data = edited_df.copy()
                            st.rerun()

                        if errors:
                            st.error(f"❌ Failed to save some changes:\n" + "\n".join(errors[:5]))
        else:
            # Read-only dataframe
            st.dataframe(df, use_container_width=True, height=500)

        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Download {selected_table} (Current Page)",
            data=csv,
            file_name=f"{selected_table}_page_{current_page}.csv",
            mime="text/csv",
        )

        # Pagination controls
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

        with col1:
            if st.button("⏮️ First", disabled=(current_page == 1), use_container_width=True):
                st.session_state.db_current_page = 1
                st.rerun()

        with col2:
            if st.button("◀️ Previous", disabled=(current_page == 1), use_container_width=True):
                st.session_state.db_current_page = max(1, current_page - 1)
                st.rerun()

        with col3:
            # Page number input
            new_page = st.number_input(
                "Go to page",
                min_value=1,
                max_value=max(1, total_pages),
                value=current_page,
                step=1,
                key="page_input",
                label_visibility="collapsed"
            )
            if new_page != current_page:
                st.session_state.db_current_page = new_page
                st.rerun()

        with col4:
            if st.button("Next ▶️", disabled=(current_page >= total_pages), use_container_width=True):
                st.session_state.db_current_page = min(total_pages, current_page + 1)
                st.rerun()

        with col5:
            if st.button("Last ⏭️", disabled=(current_page >= total_pages), use_container_width=True):
                st.session_state.db_current_page = total_pages
                st.rerun()

# ============================================================================
# TAB 2: SCHEMA VIEWER
# ============================================================================

with tab2:
    st.markdown("""
        <div class="title-card">
            <h3>Database Schema Viewer</h3>
            <p>
                View the structure of database tables, including column names, types, and constraints.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Table selection for schema
    schema_table = st.selectbox(
        "Select Table to View Schema",
        options=tables,
        index=tables.index(st.session_state.db_selected_table) if st.session_state.db_selected_table in tables else 0,
        key="schema_table_selector"
    )

    # Fetch schema
    with st.spinner(f"Loading schema for {schema_table}..."):
        schema_response = get_table_schema(schema_table)

    if not schema_response.get("success"):
        st.error(f"Failed to load table schema: {schema_response.get('error', 'Unknown error')}")
        st.stop()

    columns = schema_response.get("columns", [])

    if not columns:
        st.warning(f"No schema information available for {schema_table}")
    else:
        # Display table name
        st.markdown(f"""
        <div style="background: var(--claude-surface); border: 1px solid var(--claude-border); border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
            <h4 style="color: var(--claude-orange); margin: 0;">{schema_table}</h4>
        </div>
        """, unsafe_allow_html=True)

        # Create schema dataframe
        schema_df = pd.DataFrame(columns)

        # Format schema display
        schema_display = schema_df.copy()
        schema_display['Primary Key'] = schema_display['pk'].apply(lambda x: '🔑' if x else '')
        schema_display['Not Null'] = schema_display['notnull'].apply(lambda x: '✓' if x else '')
        schema_display = schema_display[['name', 'type', 'Primary Key', 'Not Null', 'default_value']]
        schema_display.columns = ['Column Name', 'Type', 'PK', 'Required', 'Default Value']

        st.dataframe(schema_display, use_container_width=True, height=500)

        # Show column count
        st.caption(f"Total columns: {len(columns)}")

        # Show primary key info
        pk_cols = [col['name'] for col in columns if col['pk']]
        if pk_cols:
            st.info(f"Primary Key: {', '.join(pk_cols)}")

        # Download schema button
        schema_csv = schema_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Download Schema for {schema_table}",
            data=schema_csv,
            file_name=f"{schema_table}_schema.csv",
            mime="text/csv",
        )
