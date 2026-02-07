"""
Streamlit web application for Louisiana Coastal Bird Monitoring Copilot.

Main application interface that integrates:
- User input (natural language questions)
- Query planning (Claude LLM)
- Data queries (DuckDB)
- Visualizations (Plotly charts)
- AI explanations (Claude responses)

Person 3 (Frontend Developer) implementation
"""

import streamlit as st
import os
from pathlib import Path

# TODO: Import modules once implemented
# from src.llm.planner import QueryPlanner
# from src.llm.formatter import ResponseFormatter
# from src.data import queries
# from src.app.charts import create_chart


def main():
    """Main Streamlit application."""

    # Page configuration
    st.set_page_config(
        page_title="Louisiana Coastal Bird Monitoring Copilot",
        page_icon="🦅",
        layout="wide"
    )

    # Header
    st.title("🦅 Louisiana Coastal Bird Monitoring Copilot")
    st.markdown(
        "Ask questions about Louisiana coastal bird populations in natural language. "
        "Data from NOAA DIVER Deepwater Horizon Avian Monitoring Database (2010-2021)."
    )

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        st.error(
            "⚠️ OPENROUTER_API_KEY not found. "
            "Please set it in your .env file or environment variables."
        )
        st.stop()

    # Initialize session state
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []

    # User input
    user_question = st.text_input(
        "Ask a question about bird populations:",
        placeholder="e.g., Show brown pelican trends from 2015-2021 in Louisiana",
        key="user_input"
    )

    # Example queries
    with st.expander("📝 Example Queries"):
        st.markdown("""
        Try asking questions like:
        - Show brown pelican trends from 2015-2021
        - What were the top 5 species in 2020?
        - Compare Terrebonne vs Plaquemines parishes
        - How did Hurricane Ida affect bird populations?
        - Tell me about the Grand Isle colony
        """)

    # Process query
    if user_question:
        with st.spinner("🔍 Analyzing your question..."):
            try:
                # TODO: Implement query processing pipeline
                # 1. Plan query with Claude
                # 2. Execute database query
                # 3. Generate visualization
                # 4. Generate AI explanation

                st.warning("⚠️ Query processing not yet implemented. Coming soon!")

                # Placeholder for results
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📊 Visualization")
                    st.info("Chart will appear here")

                with col2:
                    st.subheader("💡 AI Insights")
                    st.info("AI-generated explanation will appear here")

            except Exception as e:
                st.error(f"❌ Error processing query: {str(e)}")

    # Sidebar with information
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        This tool uses:
        - **OpenRouter** for natural language understanding
        - **DuckDB** for fast data queries
        - **Plotly** for interactive visualizations

        ### Data Coverage
        - **Years**: 2010-2021
        - **Location**: Louisiana coastal parishes
        - **Source**: NOAA DIVER Database
        """)

        st.header("🗂️ Database Status")
        db_path = Path("data/processed/bird_survey.duckdb")
        if db_path.exists():
            st.success("✅ Database loaded")
        else:
            st.warning("⚠️ Database not found. Run `python src/data/load_data.py` first.")


if __name__ == "__main__":
    main()
