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
    insert_table_row,
    execute_custom_sql,
    get_version_history,
    get_version_stats,
    get_version_diff,
    rollback_database,
    manual_version_commit
)
from components import init_page, render_header, render_sidebar

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

# Initialize page with shared layout
init_page(page_title="NestDB - NestScope", page_icon="🗄️", layout="wide")

# Render shared header
render_header(page_name="NestDB")

# Add custom CSS for proper scrolling in tabs and clean version history
st.markdown("""
<style>
    /* Fix tab content scrolling */
    .stTabs [data-baseweb="tab-panel"] {
        max-height: calc(100vh - 200px);
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 0.5rem;
    }

    /* Ensure expanders within tabs are scrollable */
    .stTabs [data-baseweb="tab-panel"] .streamlit-expanderContent {
        max-height: none;
    }

    /* Add padding at bottom of tab content so last items aren't hidden */
    .stTabs [data-baseweb="tab-panel"] > div {
        padding-bottom: 3rem;
    }

    /* Improve scrollbar visibility in tab panels */
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

    /* Clean version history styling (Google Docs-like) */
    .stContainer {
        background: var(--claude-surface);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-left: 3px solid var(--claude-border);
        transition: border-color 0.2s;
    }

    .stContainer:hover {
        border-left-color: var(--claude-orange);
    }
</style>
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

# User email session state (for version control attribution)
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if "vc_search_query" not in st.session_state:
    st.session_state.vc_search_query = ""

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Render shared navigation, tools, and status
    render_sidebar(active_page="nestdb")

# ============================================================================
# MAIN INTERFACE
# ============================================================================

st.title("NestDB")
st.caption("Database management interface - view, edit, and add data with full version control")

# User Email Input (for attribution)
col1, col2 = st.columns([3, 1])
with col1:
    user_email = st.text_input(
        "Your email (for change attribution)",
        value=st.session_state.user_email,
        placeholder="your.email@example.com",
        key="user_email_input",
        help="All changes you make will be attributed to this email in version history"
    )
    if user_email != st.session_state.user_email:
        st.session_state.user_email = user_email

with col2:
    # Version Control Status
    version_stats = get_version_stats()
    if version_stats.get("success"):
        total_commits = version_stats.get("total_commits", 0)
        st.metric("Total Commits", f"{total_commits:,}")
    else:
        st.warning("⚠️ Version control not active")

# Create tabs for Table Browser, Schema Viewer, SQL Query Editor, and Version History
tab1, tab2, tab3, tab4 = st.tabs(["📊 Table Browser", "📋 Schema Viewer", "⚙️ SQL Query Editor", "🕐 Version History"])

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
                            response = insert_table_row(selected_table, new_row_data, expert_email=st.session_state.user_email)

                            if response.get("success"):
                                success_msg = f"✅ {response.get('message', 'Row inserted successfully')}"
                                if response.get("version_commit"):
                                    success_msg += f" (commit `{response['version_commit']}`)"
                                st.success(success_msg)
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
                                    response = update_table_row(selected_table, row_id, updates, expert_email=st.session_state.user_email)

                                    if response.get("success"):
                                        changes_saved += 1
                                    else:
                                        errors.append(f"Row {idx + 1}: {response.get('error', 'Unknown error')}")

                        # Show results
                        if changes_saved > 0:
                            # Check if the last response included version control info
                            if response.get("version_commit"):
                                st.success(f"✅ Successfully saved {changes_saved} row(s) (commit `{response['version_commit']}`)")
                            else:
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

# ============================================================================
# TAB 3: SQL QUERY EDITOR
# ============================================================================

with tab3:
    st.markdown("""
        <div class="title-card">
            <h3>SQL Query Editor</h3>
            <p>
                Execute custom SQL queries directly against the database.
                Write SELECT, JOIN, or complex analytical queries for advanced data exploration.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Initialize session state for query history
    if "sql_query_history" not in st.session_state:
        st.session_state.sql_query_history = []

    if "sql_last_query" not in st.session_state:
        st.session_state.sql_last_query = ""

    # Example queries section
    with st.expander("📚 Example Queries", expanded=False):
        st.markdown("""
        **Basic Queries:**
        ```sql
        -- View all observations from Texas
        SELECT * FROM observations WHERE State = 'TX' LIMIT 100;

        -- Count observations by year
        SELECT Year, COUNT(*) as count
        FROM observations
        GROUP BY Year
        ORDER BY Year;

        -- Top 10 colonies by total bird count
        SELECT ColonyName, SUM(Total) as TotalBirds
        FROM observations
        GROUP BY ColonyName
        ORDER BY TotalBirds DESC
        LIMIT 10;
        ```

        **Advanced Queries:**
        ```sql
        -- Species diversity by state
        SELECT State, COUNT(DISTINCT Species) as SpeciesCount
        FROM observations
        GROUP BY State
        ORDER BY SpeciesCount DESC;

        -- Year-over-year growth for a specific colony
        SELECT Year, Total,
               Total - LAG(Total) OVER (ORDER BY Year) as YearOverYearChange
        FROM observations
        WHERE ColonyName = 'Your Colony Name Here'
        ORDER BY Year;
        ```
        """)

    # Query input area
    st.markdown("### Write Your Query")
    sql_query = st.text_area(
        "SQL Query",
        value=st.session_state.sql_last_query,
        height=200,
        placeholder="SELECT * FROM observations LIMIT 100;",
        help="Write your SQL query here. Use standard SQLite syntax.",
        label_visibility="collapsed"
    )

    # Execute button and safety note
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        execute_button = st.button("▶️ Execute Query", type="primary", use_container_width=True)

    # Safety warning
    st.info("💡 **Tip:** You can execute any SQL query here. Write operations (INSERT, UPDATE, DELETE) are automatically tracked in version history with your email.")

    # Execute query
    if execute_button:
        if not sql_query.strip():
            st.warning("Please enter a SQL query.")
        else:
            # Store query in session state
            st.session_state.sql_last_query = sql_query

            # Add to history if not duplicate
            if sql_query not in st.session_state.sql_query_history:
                st.session_state.sql_query_history.insert(0, sql_query)
                # Keep only last 10 queries
                st.session_state.sql_query_history = st.session_state.sql_query_history[:10]

            with st.spinner("Executing query..."):
                response = execute_custom_sql(sql_query, expert_email=st.session_state.user_email)

            # Display results
            if response.get("success"):
                results = response.get("results", [])
                results_count = response.get("results_count", 0)

                st.success(f"✅ Query executed successfully! Returned {results_count:,} row(s).")

                if results_count > 0:
                    # Convert to dataframe
                    results_df = pd.DataFrame(results)

                    # Display results
                    st.markdown("### Query Results")
                    st.dataframe(results_df, use_container_width=True, height=400)

                    # Download button
                    csv = results_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"📥 Download Results ({results_count} rows)",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("Query executed successfully but returned no rows.")

            else:
                error_msg = response.get("error", "Unknown error")
                st.error(f"❌ Query failed: {error_msg}")

                # Show helpful error tips
                with st.expander("💡 Common Error Solutions"):
                    st.markdown("""
                    **Table doesn't exist?**
                    - Check the Schema Viewer tab for available tables
                    - Table names are case-sensitive

                    **Syntax error?**
                    - SQLite uses standard SQL syntax
                    - Use single quotes for strings: `'TX'` not `"TX"`
                    - End statements with semicolon (optional)

                    **Column doesn't exist?**
                    - Check the Schema Viewer for correct column names
                    - Column names are case-sensitive
                    """)

    # Query history section
    if st.session_state.sql_query_history:
        st.markdown("---")
        st.markdown("### 📜 Query History")

        for idx, hist_query in enumerate(st.session_state.sql_query_history[:5]):
            with st.expander(f"Query {idx + 1}: {hist_query[:50]}..."):
                st.code(hist_query, language="sql")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(f"↩️ Reuse", key=f"reuse_{idx}", use_container_width=True):
                        st.session_state.sql_last_query = hist_query
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Remove", key=f"remove_{idx}", use_container_width=True):
                        st.session_state.sql_query_history.pop(idx)
                        st.rerun()

# ============================================================================
# TAB 4: VERSION HISTORY (Git-based Database Versioning)
# ============================================================================

with tab4:
    st.markdown("""
        <div class="title-card">
            <h3>Version History</h3>
            <p>
                Every change is automatically tracked. View the complete timeline, compare versions, and restore any previous state.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Fetch version control stats
    stats = get_version_stats()

    if not stats.get("success"):
        st.error(f"Version control unavailable: {stats.get('error', 'Unknown error')}")
        st.stop()

    # Controls: search and limit
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        search_query = st.text_input(
            "🔍 Search history",
            placeholder="Search by message, author, or commit hash...",
            key="vc_search_input"
        )

    with col2:
        history_limit = st.selectbox(
            "Show commits",
            options=[10, 25, 50, 100],
            index=1,
            key="history_limit"
        )

    with col3:
        st.metric("Commits", f"{stats.get('total_commits', 0)}", help="Total tracked changes")

    # Fetch commit history
    with st.spinner("Loading version history..."):
        history_response = get_version_history(limit=history_limit)

    if not history_response.get("success"):
        st.error(f"Failed to load history: {history_response.get('error', 'Unknown error')}")
        st.stop()

    commits = history_response.get("commits", [])

    if not commits:
        st.info("No commits found. Make some database changes to see version history.")
    else:
        # Filter commits based on search query
        if search_query:
            filtered_commits = [
                c for c in commits
                if search_query.lower() in c['message'].lower()
                or search_query.lower() in c['author'].lower()
                or search_query.lower() in c['hash_short'].lower()
            ]

            if not filtered_commits:
                st.warning(f"No commits found matching '{search_query}'")
                filtered_commits = commits
        else:
            filtered_commits = commits

        st.caption(f"Showing {len(filtered_commits)} of {len(commits)} commits")
        st.markdown("---")

        # Display commits with Google Docs-style clean UI
        for idx, commit in enumerate(filtered_commits):
            # Determine if this is the current version
            is_current = (idx == 0 and not search_query)

            # Create a clean card-like layout for each commit
            with st.container():
                # Header row with timestamp, author, and current badge
                header_col1, header_col2, header_col3 = st.columns([2, 2, 1])

                with header_col1:
                    # Relative time display (like Google Docs)
                    st.markdown(f"**{commit['date']}**")

                with header_col2:
                    # Author name
                    st.markdown(f"*{commit['author']}*")

                with header_col3:
                    if is_current:
                        st.markdown("🟢 **Current**")
                    else:
                        st.markdown(f"`{commit['hash_short']}`")

                # Commit message (main content) - FULL, NO TRUNCATION
                st.markdown(f"{commit['message']}")

                # Show detailed commit information if available
                if commit.get('details'):
                    with st.expander("📋 View details", expanded=False):
                        details = commit.get('details', {})

                        # Display each detail field
                        for key, value in details.items():
                            # Format the key nicely
                            formatted_key = key.replace('_', ' ').title()

                            # For long values (like SQL queries), show in code block
                            if key == 'query' or len(str(value)) > 100:
                                st.markdown(f"**{formatted_key}:**")
                                st.code(value, language='sql' if key == 'query' else None)
                            else:
                                st.markdown(f"**{formatted_key}:** `{value}`")

                # Action buttons in a subtle row
                action_col1, action_col2, action_col3, action_col4 = st.columns([1, 1, 1, 3])

                with action_col1:
                    if st.button("View changes", key=f"view_diff_{commit['hash_short']}", use_container_width=True):
                        st.session_state[f"show_diff_{commit['hash_short']}"] = True
                        st.rerun()

                with action_col2:
                    if not is_current:
                        if st.button("Restore", key=f"rollback_{commit['hash_short']}", use_container_width=True):
                            st.session_state[f"confirm_rollback_{commit['hash_short']}"] = True
                            st.rerun()

                with action_col3:
                    if st.button("Copy hash", key=f"copy_{commit['hash_short']}", use_container_width=True):
                        st.code(commit['hash'], language=None)
                        st.caption("Full hash displayed above ↑")

                # Show diff if requested
                if st.session_state.get(f"show_diff_{commit['hash_short']}", False):
                    with st.spinner("Loading changes..."):
                        diff_response = get_version_diff(commit_hash=commit['hash'])

                        if diff_response.get("success"):
                            diff_text = diff_response.get('diff', '')

                            if diff_text:
                                # Show a preview of the diff (first 30 lines)
                                diff_lines = diff_text.split('\n')
                                if len(diff_lines) > 30:
                                    st.code('\n'.join(diff_lines[:30]), language="diff")
                                    st.caption(f"Showing first 30 lines of {len(diff_lines)} total")

                                    if st.button("Show full diff", key=f"show_full_diff_{commit['hash_short']}"):
                                        st.code(diff_text, language="diff")
                                else:
                                    st.code(diff_text, language="diff")
                            else:
                                st.info("No changes to display")

                            if st.button("Hide", key=f"hide_diff_{commit['hash_short']}"):
                                st.session_state[f"show_diff_{commit['hash_short']}"] = False
                                st.rerun()
                        else:
                            st.error(f"Failed to load diff: {diff_response.get('error', 'Unknown error')}")

                # Rollback confirmation
                if st.session_state.get(f"confirm_rollback_{commit['hash_short']}", False):
                    st.warning(f"""
⚠️ **Restore this version?**

This will undo all changes made after this commit. A safety backup will be created automatically.
                    """)

                    # Count how many commits will be affected
                    commits_to_undo = idx
                    if commits_to_undo > 0:
                        st.error(f"This will undo **{commits_to_undo} commit(s)**")

                    rollback_col1, rollback_col2 = st.columns([1, 1])

                    with rollback_col1:
                        if st.button("Confirm restore", key=f"confirm_rollback_yes_{commit['hash_short']}", type="primary", use_container_width=True):
                            with st.spinner("Restoring version..."):
                                rollback_result = rollback_database(
                                    commit_hash=commit['hash'],
                                    expert_email=st.session_state.user_email or "anonymous"
                                )

                                if rollback_result.get("success"):
                                    st.success(f"✅ Version restored successfully!")
                                    st.caption(f"Backup saved: `{rollback_result.get('snapshot_path', 'N/A')}`")

                                    # Clear confirmation state
                                    st.session_state[f"confirm_rollback_{commit['hash_short']}"] = False

                                    st.rerun()
                                else:
                                    st.error(f"❌ Restore failed: {rollback_result.get('error', 'Unknown error')}")

                    with rollback_col2:
                        if st.button("Cancel", key=f"confirm_rollback_no_{commit['hash_short']}", use_container_width=True):
                            st.session_state[f"confirm_rollback_{commit['hash_short']}"] = False
                            st.rerun()

                # Divider between commits
                st.markdown("---")


