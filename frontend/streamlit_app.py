import streamlit as st
import asyncio
import time
import json
from datetime import datetime
from typing import Dict, Optional
import aiohttp

# Configure page
st.set_page_config(
    page_title="AI Research Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .status-running {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
    }
    .status-completed {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
    }
    .status-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        text-align: center;
    }
    .export-section {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# API configuration
API_BASE_URL = "http://localhost:8000"

class ResearchApp:
    """Streamlit application for AI Research Agent"""

    def __init__(self):
        self.api_url = API_BASE_URL

    def run(self):
        """Main application entry point"""
        st.markdown('<h1 class="main-header">🔍 AI Research Agent</h1>', unsafe_allow_html=True)
        st.markdown("---")

        # Sidebar
        self._render_sidebar()

        # Main content
        self._render_main_content()

    def _render_sidebar(self):
        """Render sidebar with configuration options"""
        with st.sidebar:
            st.header("⚙️ Configuration")

            # Research settings
            st.subheader("Research Settings")
            max_results = st.slider("Max Results", 5, 20, 10)
            freshness = st.selectbox(
                "Time Filter",
                ["", "day", "week", "month", "year"],
                format_func=lambda x: "Any time" if x == "" else x.capitalize()
            )

            style = st.selectbox(
                "Summary Style",
                ["comprehensive", "brief", "technical"],
                format_func=lambda x: x.capitalize()
            )

            # Search engines
            st.subheader("Search Engines")
            use_duckduckgo = st.checkbox("DuckDuckGo", value=True)
            use_brave = st.checkbox("Brave Search", value=False)

            # Store settings in session state
            st.session_state.max_results = max_results
            st.session_state.freshness = freshness if freshness else None
            st.session_state.style = style
            st.session_state.search_engines = []
            if use_duckduckgo:
                st.session_state.search_engines.append("duckduckgo")
            if use_brave:
                st.session_state.search_engines.append("brave")

            # API status
            st.markdown("---")
            self._render_api_status()

    def _render_api_status(self):
        """Render API connection status"""
        try:
            # Simple health check
            response = asyncio.run(self._check_api_health())
            if response:
                st.success("✅ API Connected")
            else:
                st.error("❌ API Not Available")
        except:
            st.error("❌ API Not Available")

    def _render_main_content(self):
        """Render main content area"""
        # Research input
        st.header("🔎 Start Research")

        query = st.text_area(
            "Enter your research query:",
            placeholder="e.g., What are the latest developments in quantum computing?",
            height=100
        )

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("🚀 Start Research", type="primary", use_container_width=True):
                if query.strip():
                    self._start_research(query.strip())
                else:
                    st.error("Please enter a research query")

        with col2:
            if st.button("📋 View History", use_container_width=True):
                self._show_history()

        with col3:
            if st.button("🗂️ Export Results", use_container_width=True):
                self._show_export_options()

        # Results display
        if "current_job" in st.session_state:
            self._render_job_status()

        if "results" in st.session_state:
            self._render_results()

    def _start_research(self, query: str):
        """Start a new research job"""
        try:
            job_data = {
                "query": query,
                "max_results": st.session_state.get("max_results", 10),
                "freshness": st.session_state.get("freshness"),
                "style": st.session_state.get("style", "comprehensive"),
                "search_engines": st.session_state.get("search_engines", ["duckduckgo"])
            }

            response = asyncio.run(self._call_api("POST", "/research", job_data))

            if response and "job_id" in response:
                st.session_state.current_job = response["job_id"]
                st.session_state.job_start_time = time.time()
                st.success(f"Research started! Job ID: {response['job_id']}")
                st.rerun()
            else:
                st.error("Failed to start research")

        except Exception as e:
            st.error(f"Error starting research: {str(e)}")

    def _render_job_status(self):
        """Render current job status"""
        job_id = st.session_state.current_job

        try:
            status_data = asyncio.run(self._call_api("GET", f"/research/status/{job_id}"))

            if status_data:
                status = status_data.get("status", "unknown")
                progress = status_data.get("progress", 0)

                # Status box
                status_class = f"status-{status}"
                st.markdown(f"""
                <div class="status-box {status_class}">
                    <h4>Job Status: {status.upper()}</h4>
                    <div>Progress: {progress}%</div>
                    <div>Job ID: {job_id}</div>
                </div>
                """, unsafe_allow_html=True)

                # Progress bar
                st.progress(progress / 100)

                # Auto-refresh for running jobs
                if status in ["starting", "searching", "extracting", "summarizing"]:
                    time.sleep(2)
                    st.rerun()

                # Get results when completed
                elif status == "completed":
                    self._fetch_results(job_id)

        except Exception as e:
            st.error(f"Error checking job status: {str(e)}")

    def _fetch_results(self, job_id: str):
        """Fetch completed research results"""
        try:
            results = asyncio.run(self._call_api("GET", f"/research/results/{job_id}"))

            if results:
                st.session_state.results = results
                st.session_state.current_job = None
                st.success("Research completed!")
                st.rerun()

        except Exception as e:
            st.error(f"Error fetching results: {str(e)}")

    def _render_results(self):
        """Render research results"""
        results = st.session_state.results

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Sources Found", results.get("extracted_count", 0))
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.metric("Search Engines", len(results.get("search_engines_used", [])))

        with col3:
            st.metric("Word Count", results.get("summary", {}).get("word_count", 0))

        with col4:
            cost = results.get("summary", {}).get("cost", 0)
            st.metric("Cost", ".4f")

        # Summary
        st.header("📋 Summary")
        summary = results.get("summary", {})

        if summary.get("summary"):
            st.write(summary["summary"])
        else:
            st.warning("No summary available")

        # Sections
        if summary.get("sections"):
            for section_name, section_content in summary["sections"].items():
                with st.expander(f"📄 {section_name}"):
                    st.write(section_content)

        # Sources
        if summary.get("sources"):
            st.header("🔗 Sources")
            for source in summary["sources"]:
                with st.expander(f"📖 {source.get('title', 'Unknown')}"):
                    st.write(f"**URL:** {source.get('url', 'N/A')}")
                    st.write(f"**Reliability:** {source.get('reliability_score', 0.5):.2f}")

        # Export section
        self._render_export_section(results)

    def _render_export_section(self, results: Dict):
        """Render export options"""
        st.markdown('<div class="export-section">', unsafe_allow_html=True)
        st.header("📤 Export Results")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📄 Export as PDF", use_container_width=True):
                self._export_pdf(results)

        with col2:
            if st.button("📝 Export as Markdown", use_container_width=True):
                self._export_markdown(results)

        with col3:
            if st.button("📊 Export as JSON", use_container_width=True):
                self._export_json(results)

        st.markdown('</div>', unsafe_allow_html=True)

    def _export_pdf(self, results: Dict):
        """Export results as PDF"""
        try:
            export_data = {"format": "pdf", "data": results}
            response = asyncio.run(self._call_api("POST", "/export", export_data))

            if response and "file_path" in response:
                st.success(f"PDF exported: {response['file_path']}")
            else:
                st.error("Failed to export PDF")

        except Exception as e:
            st.error(f"Error exporting PDF: {str(e)}")

    def _export_markdown(self, results: Dict):
        """Export results as Markdown"""
        try:
            export_data = {"format": "markdown", "data": results}
            response = asyncio.run(self._call_api("POST", "/export", export_data))

            if response and "file_path" in response:
                st.success(f"Markdown exported: {response['file_path']}")
            else:
                st.error("Failed to export Markdown")

        except Exception as e:
            st.error(f"Error exporting Markdown: {str(e)}")

    def _export_json(self, results: Dict):
        """Export results as JSON"""
        try:
            export_data = {"format": "json", "data": results}
            response = asyncio.run(self._call_api("POST", "/export", export_data))

            if response and "file_path" in response:
                st.success(f"JSON exported: {response['file_path']}")
            else:
                st.error("Failed to export JSON")

        except Exception as e:
            st.error(f"Error exporting JSON: {str(e)}")

    def _show_history(self):
        """Show research history"""
        st.header("📚 Research History")
        st.info("History feature coming soon!")

    def _show_export_options(self):
        """Show export options"""
        st.header("📤 Export Options")
        st.info("Use the export buttons in the results section")

    async def _call_api(self, method: str, endpoint: str, data: Optional[Dict] = None):
        """Make API call to backend"""
        url = f"{self.api_url}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            return None
                elif method == "POST":
                    async with session.post(url, json=data) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            return None
        except:
            return None

    async def _check_api_health(self) -> bool:
        """Check if API is healthy"""
        try:
            result = await self._call_api("GET", "/health")
            return result is not None
        except:
            return False

def main():
    """Main application entry point"""
    app = ResearchApp()
    app.run()

if __name__ == "__main__":
    main()