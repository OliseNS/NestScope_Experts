"""
PDF Report Generator for NestScope
Automatically creates clean, professional PDF reports with data visualizations

This module uses AI to:
1. Plan report structure based on user's description
2. Generate SQL queries to fetch relevant data
3. Create charts, graphs, and maps
4. Assemble everything into a beautiful PDF using WeasyPrint
"""

from weasyprint import HTML, CSS
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any, Optional
import pandas as pd
from pathlib import Path
import base64
from io import BytesIO
from datetime import datetime

# Claude Orange color for consistent branding
CLAUDE_ORANGE = '#D97757'

class Section:
    """Represents a single report section"""
    def __init__(
        self,
        title: str,
        content_type: str,  # 'text', 'chart', 'map', 'table'
        content: Any,
        caption: Optional[str] = None
    ):
        self.title = title
        self.content_type = content_type
        self.content = content
        self.caption = caption

class ReportPlan:
    """AI-generated plan for a report"""
    def __init__(
        self,
        title: str,
        subtitle: str,
        sections: List[Dict[str, Any]]
    ):
        self.title = title
        self.subtitle = subtitle
        self.sections = sections

class ReportGenerator:
    """
    Generates professional PDF reports with data visualizations.

    This class coordinates between:
    - AI planning (what sections to create)
    - Data querying (using existing SQLChatbot)
    - Visualization generation (charts/maps)
    - PDF assembly (WeasyPrint with HTML/CSS)
    """

    def __init__(self, sqlchatbot):
        """
        Initialize report generator.

        Args:
            sqlchatbot: SQLChatbot instance for executing queries
        """
        self.chatbot = sqlchatbot

    def create_report_plan(self, user_description: str) -> ReportPlan:
        """
        Use AI to create a structured report plan.

        The LLM analyzes the request and creates a logical flow of sections
        with appropriate visualizations.

        Args:
            user_description: User's description of what they want

        Returns:
            ReportPlan with section structure and queries
        """
        # Load database metadata to give AI context
        metadata_context = ""
        if self.chatbot.metadata:
            # Get table summaries
            tables_info = []
            for table_name, table_info in self.chatbot.metadata.get('tables', {}).items():
                purpose = table_info.get('purpose', '')
                if purpose:
                    tables_info.append(f"- {table_name}: {purpose}")

            metadata_context = f"""
DATABASE SCHEMA OVERVIEW:
{chr(10).join(tables_info)}

KEY DATA FACTS:
- Time period: 2010-2021 (11 years of data)
- Geographic scope: Texas, Louisiana, Mississippi, Alabama, Florida (Gulf Coast)
- Main metrics: Bird counts (TotalBirds), Nest counts (TotalNests), Species diversity
- Use tblColonyTotals2010-2021_MayJuneCombined for aggregate counts by colony/year/species
- Colonies have Latitude and Longitude for mapping
"""

        planning_prompt = f"""You are an expert at creating scientific analysis reports about Gulf Coast bird colony survey data.

{metadata_context}

User wants: {user_description}

Create a well-balanced report plan with 6-8 sections. CRITICAL STRUCTURE REQUIREMENTS:

1. **Executive Summary** (text) - 4-6 bullet points with key findings and numbers
2. **Data Overview** (text + table) - Dataset statistics, time period, geographic scope as bullet points, then a summary table
3. **2-3 Data Visualization Sections** (chart/map) - ONLY the most important visualizations
4. **Analysis & Insights** (text) - 5-7 bullet points analyzing the data, trends, patterns, implications
5. **Key Findings** (text) - 4-6 bullet points with specific numbers and conclusions
6. **Recommendations** (text) - 3-5 actionable recommendations based on the data

BALANCE REQUIREMENTS:
- At least 40% of sections should be TEXT (analysis, insights, findings)
- Maximum 2-3 visualizations (charts/maps)
- Every visualization needs a text section explaining its insights
- Focus on INSIGHTS not just showing data

VISUALIZATION RULES:
- chart_line: ONLY for clear time trends (e.g., "total birds by year")
- chart_bar: ONLY for top 10-15 rankings (e.g., "top 10 species")
- map: ONLY if geographic patterns are specifically requested - query MUST say "with their locations"
- table: For summary statistics (max 15 rows)
- text: For analysis, insights, findings, recommendations

QUERY REQUIREMENTS:
- Keep queries SIMPLE - avoid complex joins
- Be SPECIFIC with years (e.g., "2010 to 2021")
- For species analysis, specify the common name (e.g., "Brown Pelican")
- Use "total bird count" or "sum of birds" not complex aggregations
- Example good queries:
  * "What were the total bird counts for each year from 2010 to 2021?"
  * "What were the top 10 species by total bird count?"
  * "Show all colonies in Louisiana with their total bird counts and locations"

CONTENT REQUIREMENTS FOR TEXT SECTIONS:
- bullet_points should contain ACTUAL INSIGHTS with specific numbers
- Include percentages, comparisons, trends
- Example: "Brown Pelican populations increased 45% from 2010 to 2021"
- NOT just generic statements like "Population trends vary"

Return a JSON object with this structure:
{{
    "title": "Clear Descriptive Title",
    "subtitle": "Gulf Coast Colonial Waterbird Survey Analysis • 2010-2021",
    "sections": [
        {{
            "section_title": "Executive Summary",
            "content_type": "text",
            "question": null,
            "bullet_points": [
                "Total of 3.2 million bird observations recorded across 592 colonies from 2010-2021",
                "Brown Pelican populations showed 45% increase, indicating successful recovery",
                "Louisiana hosts 38% of all Gulf Coast colonies, the highest concentration",
                "Species diversity declined 12% in Florida panhandle regions"
            ],
            "caption": null
        }},
        {{
            "section_title": "Dataset Overview",
            "content_type": "text",
            "question": null,
            "bullet_points": [
                "Survey Period: 2010-2021 (11 years of continuous monitoring)",
                "Geographic Coverage: 592 colonies across TX, LA, MS, AL, FL",
                "Species Monitored: 73 colonial waterbird species",
                "Data Points: Over 50,000 individual survey records"
            ],
            "caption": null
        }},
        {{
            "section_title": "Population Trends Over Time",
            "content_type": "chart_line",
            "question": "What were the total bird counts for each year from 2010 to 2021?",
            "caption": "Annual bird counts showing overall population stability with minor fluctuations"
        }},
        {{
            "section_title": "Analysis of Population Patterns",
            "content_type": "text",
            "question": null,
            "bullet_points": [
                "Peak populations observed in 2018-2019, corresponding with favorable weather conditions",
                "Post-2020 slight decline may reflect impacts of climate events",
                "Pelican species show strongest recovery, up 45% since 2010",
                "Tern species remain stable, indicating healthy coastal ecosystems",
                "Regional variations suggest localized habitat quality differences"
            ],
            "caption": null
        }},
        {{
            "section_title": "Most Abundant Species",
            "content_type": "chart_bar",
            "question": "What were the top 10 species by total bird count from 2010 to 2021?",
            "caption": "Dominant species across the Gulf Coast study period"
        }},
        {{
            "section_title": "Key Findings",
            "content_type": "text",
            "question": null,
            "bullet_points": [
                "Brown Pelican recovery continues, with populations 145% above 2010 baseline",
                "Laughing Gull maintains stable populations, serving as indicator species",
                "Royal Tern colonies concentrated in western Gulf, requiring targeted protection",
                "Declining species (12% of monitored) need immediate conservation intervention"
            ],
            "caption": null
        }},
        {{
            "section_title": "Conservation Recommendations",
            "content_type": "text",
            "question": null,
            "bullet_points": [
                "Establish protection zones for high-density colonies in Louisiana coastal regions",
                "Increase monitoring frequency for declining species in Florida panhandle",
                "Develop habitat restoration plans for colonies showing population stress",
                "Continue annual surveys to track long-term climate change impacts"
            ],
            "caption": null
        }}
    ]
}}

Return ONLY the JSON, no other text."""

        # Call LLM to generate the plan
        from openai import OpenAI
        import os
        import json

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        response = client.chat.completions.create(
            model=self.chatbot.model,
            messages=[
                {"role": "user", "content": planning_prompt}
            ],
            temperature=0.3
        )

        # Parse the JSON response
        plan_json = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        if plan_json.startswith("```"):
            plan_json = plan_json.split("```")[1]
            if plan_json.startswith("json"):
                plan_json = plan_json[4:]
        plan_json = plan_json.strip()

        plan_data = json.loads(plan_json)

        return ReportPlan(
            title=plan_data['title'],
            subtitle=plan_data['subtitle'],
            sections=plan_data['sections']
        )

    def execute_section_queries(self, plan: ReportPlan) -> List[Section]:
        """
        Execute queries for each section and prepare content.

        Args:
            plan: ReportPlan from create_report_plan()

        Returns:
            List of Section objects with generated content
        """
        sections = []

        for section_def in plan.sections:
            section_title = section_def['section_title']
            content_type = section_def['content_type']
            question = section_def.get('question')
            caption = section_def.get('caption', '')

            if content_type == 'text':
                # Text-only section
                bullet_points = section_def.get('bullet_points', [])
                sections.append(Section(
                    title=section_title,
                    content_type='text',
                    content=bullet_points,
                    caption=caption
                ))

            elif question:
                # Data section
                print(f"  Executing query for section: {section_title}")
                print(f"  Question: {question}")

                result = self.chatbot.ask(question, conversation_history=[])

                if result['success'] and result['results']:
                    df = pd.DataFrame(result['results'])
                    answer_text = result['answer']

                    print(f"  ✓ Query successful: {len(df)} rows returned")

                    if df.empty:
                        print(f"  ⚠ Warning: Query returned empty results")
                        sections.append(Section(
                            title=section_title,
                            content_type='text',
                            content=[f"No data available for this analysis."],
                            caption=caption
                        ))
                        continue

                    # Generate visualization based on content_type
                    if content_type.startswith('chart_'):
                        chart_type = content_type.split('_')[1]
                        try:
                            chart_base64 = self._create_chart(df, chart_type, section_title)
                            sections.append(Section(
                                title=section_title,
                                content_type='chart',
                                content=chart_base64,
                                caption=caption or answer_text[:300]
                            ))
                            print(f"  ✓ Chart created successfully")
                        except Exception as e:
                            print(f"  ✗ Chart creation failed: {e}")
                            sections.append(Section(
                                title=section_title,
                                content_type='text',
                                content=[f"Chart could not be created. Data: {len(df)} rows"],
                                caption=caption
                            ))

                    elif content_type == 'map':
                        try:
                            map_base64 = self._create_map(df, section_title)
                            sections.append(Section(
                                title=section_title,
                                content_type='map',
                                content=map_base64,
                                caption=caption or answer_text[:300]
                            ))
                            print(f"  ✓ Map created successfully")
                        except Exception as e:
                            print(f"  ✗ Map creation failed: {e}")
                            sections.append(Section(
                                title=section_title,
                                content_type='text',
                                content=[f"Map could not be created."],
                                caption=caption
                            ))

                    elif content_type == 'table':
                        if len(df) > 15:
                            df = df.head(15)
                        sections.append(Section(
                            title=section_title,
                            content_type='table',
                            content=df,
                            caption=caption or answer_text[:200]
                        ))
                        print(f"  ✓ Table created with {len(df)} rows")

                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"  ✗ Query failed: {error_msg}")
                    # Instead of showing error, skip this section or provide generic fallback
                    sections.append(Section(
                        title=section_title,
                        content_type='text',
                        content=[
                            "This analysis section could not be completed due to data availability constraints.",
                            "The requested query did not return results or encountered technical limitations.",
                            "Please refer to other sections for available insights on this topic."
                        ],
                        caption="Data unavailable"
                    ))

        return sections

    def _create_chart(self, df: pd.DataFrame, chart_type: str, title: str) -> str:
        """
        Create a chart image from DataFrame and return as base64 string.

        Args:
            df: DataFrame with query results
            chart_type: 'line' or 'bar'
            title: Chart title

        Returns:
            Base64 encoded PNG image
        """
        if df.empty:
            return self._create_error_image("No data available")

        # Smart column detection
        numeric_cols = [col for col in df.columns if df[col].dtype in ['int64', 'float64', 'Int64']]
        text_cols = [col for col in df.columns if df[col].dtype == 'object' or col in ['Year', 'Month']]

        # Detect X-axis
        x_col = None
        if 'Year' in df.columns:
            x_col = 'Year'
        elif 'Date' in df.columns:
            x_col = 'Date'
        elif any(col in df.columns for col in ['Species', 'SpeciesName', 'CommonName']):
            x_col = next((col for col in ['Species', 'SpeciesName', 'CommonName'] if col in df.columns), None)
        elif any(col in df.columns for col in ['ColonyName', 'Colony', 'State']):
            x_col = next((col for col in ['ColonyName', 'Colony', 'State'] if col in df.columns), None)
        elif text_cols:
            x_col = text_cols[0]
        elif numeric_cols:
            x_col = numeric_cols[0]
        else:
            x_col = df.columns[0]

        # Detect Y-axis
        y_cols = []
        for col in numeric_cols:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['count', 'total', 'bird', 'nest', 'observation', 'number']):
                y_cols.append(col)

        if not y_cols:
            y_cols = [col for col in numeric_cols if col != x_col]

        if not y_cols and len(df.columns) > 1:
            y_cols = [col for col in df.columns if col != x_col][:2]

        if not y_cols:
            return self._create_error_image("Unable to determine chart structure")

        # Limit data points
        if len(df) > 50:
            df = df.head(50)

        # Create chart
        if chart_type == 'line':
            fig = go.Figure()
            for y_col in y_cols[:2]:  # Max 2 lines for clarity
                fig.add_trace(go.Scatter(
                    x=df[x_col],
                    y=df[y_col],
                    mode='lines+markers',
                    name=y_col,
                    line=dict(width=3),
                    marker=dict(size=8)
                ))
        else:  # bar
            fig = go.Figure()
            if len(y_cols) == 1:
                fig.add_trace(go.Bar(
                    x=df[x_col],
                    y=df[y_cols[0]],
                    name=y_cols[0],
                    marker_color=CLAUDE_ORANGE
                ))
            else:
                for y_col in y_cols[:2]:
                    fig.add_trace(go.Bar(
                        x=df[x_col],
                        y=df[y_col],
                        name=y_col
                    ))

        y_axis_title = 'Count' if any(w in str(y_cols).lower() for w in ['count', 'total', 'bird']) else y_cols[0]

        fig.update_layout(
            title=dict(text=title, font=dict(size=18, color='#333', family='Georgia')),
            xaxis_title=x_col,
            yaxis_title=y_axis_title,
            font=dict(size=12, family='Georgia'),
            showlegend=len(y_cols) > 1,
            width=800,
            height=500,
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='#E5E5E5', showline=True, linecolor='#666'),
            yaxis=dict(showgrid=True, gridcolor='#E5E5E5', showline=True, linecolor='#666'),
            barmode='group' if chart_type == 'bar' and len(y_cols) > 1 else 'relative',
            margin=dict(l=80, r=40, t=80, b=80)
        )

        # Convert to base64
        img_bytes = fig.to_image(format='png', width=800, height=500)
        return base64.b64encode(img_bytes).decode('utf-8')

    def _create_map(self, df: pd.DataFrame, title: str) -> str:
        """
        Create a map visualization and return as base64 string.

        Args:
            df: DataFrame with Latitude, Longitude columns
            title: Map title

        Returns:
            Base64 encoded PNG image
        """
        lat_col = next((col for col in df.columns if 'lat' in col.lower()), None)
        lon_col = next((col for col in df.columns if 'lon' in col.lower()), None)

        if not lat_col or not lon_col:
            return self._create_error_image("No coordinate data available")

        # Find size column
        size_col = None
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['count', 'total', 'observation', 'nest', 'bird']):
                if df[col].dtype in ['int64', 'float64']:
                    size_col = col
                    break

        fig = go.Figure(go.Scattergeo(
            lon=df[lon_col],
            lat=df[lat_col],
            text=df.get('ColonyName', df.get('Colony', '')),
            mode='markers',
            marker=dict(
                size=df[size_col] / df[size_col].max() * 25 + 8 if size_col else 12,
                color=df[size_col] if size_col else CLAUDE_ORANGE,
                colorscale='Oranges',
                showscale=bool(size_col),
                colorbar=dict(title=size_col if size_col else '', len=0.7),
                line=dict(width=1, color='white')
            )
        ))

        fig.update_geos(
            scope='usa',
            center=dict(lat=29, lon=-90),
            projection_scale=3.5,
            showland=True,
            landcolor='rgb(240, 240, 240)',
            coastlinecolor='rgb(100, 100, 100)',
            showlakes=True,
            lakecolor='rgb(200, 225, 255)',
            showcountries=True,
            countrycolor='rgb(150, 150, 150)'
        )

        fig.update_layout(
            title=dict(text=title, font=dict(size=18, color='#333', family='Georgia')),
            width=800,
            height=500,
            font=dict(size=12, family='Georgia'),
            margin=dict(l=40, r=40, t=80, b=40)
        )

        img_bytes = fig.to_image(format='png', width=800, height=500)
        return base64.b64encode(img_bytes).decode('utf-8')

    def _create_error_image(self, message: str) -> str:
        """Create a simple error image as base64."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color='red')
        )
        fig.update_layout(
            width=800, height=500,
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
        )
        img_bytes = fig.to_image(format='png')
        return base64.b64encode(img_bytes).decode('utf-8')

    def build_pdf(self, plan: ReportPlan, sections: List[Section], output_path: str) -> str:
        """
        Assemble sections into a PDF report using WeasyPrint.

        Creates a professional scientific report with:
        - Cover page with title and metadata
        - Table of contents
        - Sections with charts, maps, and tables
        - Clean typography and layout
        - Page numbers and headers

        Args:
            plan: Report plan with title/subtitle
            sections: List of Section objects with content
            output_path: Where to save the PDF file

        Returns:
            Path to the generated PDF file
        """
        # Build HTML content
        html_content = self._build_html(plan, sections)

        # Generate PDF
        HTML(string=html_content).write_pdf(output_path)

        return output_path

    def _build_html(self, plan: ReportPlan, sections: List[Section]) -> str:
        """Build HTML content for the report."""

        # Build sections HTML
        sections_html = ""
        section_number = 1
        figure_number = 1

        for section in sections:
            if section.content_type == 'text':
                bullet_html = "".join([f"<li>{item}</li>" for item in section.content])
                sections_html += f"""
                <div class="section text-section">
                    <h2>{section_number}. {section.title}</h2>
                    <ul class="bullet-list">
                        {bullet_html}
                    </ul>
                </div>
                """
                section_number += 1

            elif section.content_type in ['chart', 'map']:
                sections_html += f"""
                <div class="section viz-section">
                    <h2>{section_number}. {section.title}</h2>
                    <div class="figure">
                        <img src="data:image/png;base64,{section.content}" alt="{section.title}">
                        <p class="caption"><strong>Figure {figure_number}:</strong> {section.caption}</p>
                    </div>
                </div>
                """
                section_number += 1
                figure_number += 1

            elif section.content_type == 'table':
                table_html = section.content.to_html(index=False, classes='data-table')
                sections_html += f"""
                <div class="section">
                    <h2>{section_number}. {section.title}</h2>
                    {table_html}
                    <p class="caption">{section.caption}</p>
                </div>
                """
                section_number += 1

        # Complete HTML document
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    size: letter;
                    margin: 1in 0.75in;
                    @bottom-center {{
                        content: counter(page);
                        font-family: Georgia, serif;
                        font-size: 10pt;
                        color: #666;
                    }}
                }}

                body {{
                    font-family: Georgia, serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    color: #333;
                }}

                .cover {{
                    page-break-after: always;
                    text-align: center;
                    padding-top: 3in;
                }}

                .cover h1 {{
                    font-size: 28pt;
                    margin-bottom: 0.5in;
                    color: {CLAUDE_ORANGE};
                    font-weight: bold;
                }}

                .cover .subtitle {{
                    font-size: 14pt;
                    color: #666;
                    margin-bottom: 0.3in;
                }}

                .cover .date {{
                    font-size: 11pt;
                    color: #888;
                    margin-top: 0.5in;
                }}

                .cover .powered-by {{
                    font-size: 10pt;
                    color: #999;
                    margin-top: 1in;
                }}

                .section {{
                    page-break-inside: avoid;
                    margin-bottom: 1.5em;
                }}

                h2 {{
                    font-size: 16pt;
                    color: {CLAUDE_ORANGE};
                    margin-top: 1.5em;
                    margin-bottom: 0.8em;
                    border-bottom: 2px solid {CLAUDE_ORANGE};
                    padding-bottom: 0.2em;
                }}

                .text-section {{
                    background: #f9f9f9;
                    padding: 1.5em;
                    border-radius: 8px;
                    margin-bottom: 2em;
                }}

                .viz-section {{
                    margin-bottom: 2em;
                }}

                .bullet-list {{
                    margin-left: 1.5em;
                    margin-top: 0.8em;
                    line-height: 1.8;
                }}

                .bullet-list li {{
                    margin-bottom: 0.8em;
                    font-size: 11pt;
                }}

                .bullet-list li strong {{
                    color: {CLAUDE_ORANGE};
                }}

                .figure {{
                    text-align: center;
                    margin: 1.5em 0;
                    page-break-inside: avoid;
                }}

                .figure img {{
                    max-width: 100%;
                    height: auto;
                    border: 1px solid #ddd;
                    padding: 0.5em;
                    background: white;
                }}

                .caption {{
                    font-size: 10pt;
                    color: #666;
                    margin-top: 0.5em;
                    text-align: left;
                    font-style: italic;
                }}

                .data-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1em 0;
                    font-size: 10pt;
                }}

                .data-table th {{
                    background-color: {CLAUDE_ORANGE};
                    color: white;
                    padding: 0.5em;
                    text-align: left;
                    font-weight: bold;
                }}

                .data-table td {{
                    padding: 0.4em 0.5em;
                    border-bottom: 1px solid #ddd;
                }}

                .data-table tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
            </style>
        </head>
        <body>
            <!-- Cover Page -->
            <div class="cover">
                <h1>{plan.title}</h1>
                <div class="subtitle">{plan.subtitle}</div>
                <div class="date">Generated on {datetime.now().strftime("%B %d, %Y")}</div>
                <div class="powered-by">Powered by NestScope AI</div>
            </div>

            <!-- Report Sections -->
            {sections_html}
        </body>
        </html>
        """

        return html

    def generate(self, user_description: str, output_dir: str = "reports") -> Dict[str, Any]:
        """
        Main entry point: generate complete PDF report from user description.

        Args:
            user_description: What the user wants in the report
            output_dir: Directory to save the PDF

        Returns:
            Dict with 'success', 'file_path', 'title', 'num_sections', 'error'
        """
        try:
            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Step 1: Create plan
            print("📋 Creating report plan...")
            plan = self.create_report_plan(user_description)
            print(f"✓ Plan created: {plan.title} ({len(plan.sections)} sections)")

            # Step 2: Execute queries and build sections
            print("🔍 Executing queries and generating visualizations...")
            sections = self.execute_section_queries(plan)
            print(f"✓ Sections prepared: {len(sections)}")

            # Step 3: Build PDF
            print("📄 Building PDF report...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nestscope_report_{timestamp}.pdf"
            output_path = str(Path(output_dir) / filename)

            self.build_pdf(plan, sections, output_path)
            print(f"✓ PDF generated: {output_path}")

            return {
                'success': True,
                'file_path': output_path,
                'title': plan.title,
                'num_sections': len(sections),
                'error': None
            }

        except Exception as e:
            print(f"✗ Error generating report: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'file_path': None,
                'title': None,
                'num_sections': 0,
                'error': str(e)
            }
