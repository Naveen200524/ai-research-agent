import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from ..core.search import MultiSearcher
from ..core.extractor import ContentExtractor
from ..core.llm_manager import LLMManager
from ..core.vector_store import SemanticCache
from ..utils.cache import SQLiteCache
from ..models.schemas import (
    ResearchResult,
    ResearchSummary,
    Source,
    SearchResult,
    ExtractedContent
)
from ..core.config import settings

logger = logging.getLogger(__name__)

class ResearchOrchestrator:
    """Main orchestrator for research operations"""

    def __init__(self):
        self.searcher = MultiSearcher(brave_api_key=settings.brave_api_key)
        self.extractor = ContentExtractor()
        self.llm_manager = LLMManager()
        self.vector_cache = SemanticCache()
        self.sqlite_cache = SQLiteCache(
            db_path=settings.sqlite_db_path,
            use_memory=settings.sqlite_memory_cache
        )
        self.jobs = {}  # In-memory job tracking

    async def research(
        self,
        query: str,
        max_results: int = 10,
        freshness: Optional[str] = None,
        style: str = "comprehensive",
        search_engines: List[str] = None
    ) -> str:
        """
        Execute complete research pipeline

        Args:
            query: Research query
            max_results: Maximum search results
            freshness: Time filter
            style: Summary style
            search_engines: List of search engines to use

        Returns:
            Job ID for tracking
        """
        job_id = str(uuid4())
        self.jobs[job_id] = {
            "status": "starting",
            "progress": 0,
            "started_at": datetime.now(),
            "query": query
        }

        # Start research in background
        asyncio.create_task(self._execute_research(
            job_id, query, max_results, freshness, style, search_engines
        ))

        return job_id

    async def _execute_research(
        self,
        job_id: str,
        query: str,
        max_results: int,
        freshness: Optional[str],
        style: str,
        search_engines: List[str]
    ):
        """Execute the research pipeline"""
        try:
            self.jobs[job_id]["status"] = "searching"
            self.jobs[job_id]["progress"] = 10

            # Check cache first
            cache_key = self._generate_cache_key(query, max_results, freshness, style)
            cached_result = await self._check_cache(cache_key)

            if cached_result:
                self.jobs[job_id]["status"] = "completed"
                self.jobs[job_id]["progress"] = 100
                self.jobs[job_id]["result"] = cached_result
                self.jobs[job_id]["from_cache"] = True
                return

            # Perform web search with enhanced DuckDuckGo capabilities
            self.jobs[job_id]["status"] = "searching"
            self.jobs[job_id]["progress"] = 20

            # Detect if this is a news-related query
            news_keywords = ['news', 'latest', 'breaking', 'today', 'recent', 'update', 'announcement']
            is_news_query = any(keyword in query.lower() for keyword in news_keywords)

            async with self.searcher:
                if is_news_query and "duckduckgo" in (search_engines or ["duckduckgo"]):
                    # Use news-specific search for news queries
                    search_results = await self.searcher.search_news(
                        query=query,
                        count=max_results,
                        freshness=freshness
                    )
                    logger.info(f"Used news search for query: {query}")
                else:
                    # Use regular web search
                    search_results = await self.searcher.search(
                        query=query,
                        count=max_results,
                        freshness=freshness,
                        engines=search_engines or ["duckduckgo"]
                    )

            self.jobs[job_id]["progress"] = 40

            # Extract content from top results
            self.jobs[job_id]["status"] = "extracting"
            urls = [result["url"] for result in search_results[:max_results]]

            await self.extractor.initialize()
            extracted_contents = await self.extractor.extract_batch(
                urls=urls,
                max_concurrent=settings.max_concurrent_extractions
            )
            await self.extractor.cleanup()

            self.jobs[job_id]["progress"] = 70

            # Filter successful extractions
            valid_contents = [
                content for content in extracted_contents
                if content.get("success") and content.get("text", "").strip()
            ]

            # Generate summary
            self.jobs[job_id]["status"] = "summarizing"
            self.jobs[job_id]["progress"] = 85

            if valid_contents:
                summary = await self.llm_manager.generate_summary(
                    query=query,
                    contents=valid_contents,
                    style=style
                )
            else:
                summary = self._create_empty_summary()

            # Create result object
            result = ResearchResult(
                job_id=job_id,
                query=query,
                search_engines_used=search_engines or ["duckduckgo"],
                search_results=[
                    SearchResult(**result) for result in search_results
                ],
                extracted_count=len(valid_contents),
                summary=ResearchSummary(**summary),
                completed_at=datetime.now(),
                from_cache=False
            )

            # Cache the result
            await self._cache_result(cache_key, result.dict())

            # Update job status
            self.jobs[job_id]["status"] = "completed"
            self.jobs[job_id]["progress"] = 100
            self.jobs[job_id]["result"] = result

        except Exception as e:
            logger.error(f"Research failed for job {job_id}: {e}")
            self.jobs[job_id]["status"] = "failed"
            self.jobs[job_id]["error"] = str(e)

    async def get_result(self, job_id: str) -> Optional[Dict]:
        """Get research result for job"""
        job = self.jobs.get(job_id)
        if not job or job.get("status") != "completed":
            return None

        result = job.get("result")
        if isinstance(result, ResearchResult):
            return result.dict()

        return result

    def get_job_status(self, job_id: str) -> Dict:
        """Get job status"""
        job = self.jobs.get(job_id)
        if not job:
            return {
                "status": "not_found",
                "progress": 0,
                "started_at": None,
                "error": None
            }

        return {
            "status": job["status"],
            "progress": job["progress"],
            "started_at": job["started_at"],
            "error": job.get("error")
        }

    def _generate_cache_key(self, query: str, max_results: int,
                           freshness: Optional[str], style: str) -> str:
        """Generate cache key for research query"""
        key_data = f"{query}|{max_results}|{freshness}|{style}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _check_cache(self, cache_key: str) -> Optional[Dict]:
        """Check for cached research result"""
        # Check semantic cache first
        semantic_result = await self.vector_cache.search_similar(cache_key)
        if semantic_result:
            return semantic_result

        # Check SQLite cache
        cached = await self.sqlite_cache.get(cache_key)
        if cached:
            return json.loads(cached)

        return None

    async def _cache_result(self, cache_key: str, result: Dict):
        """Cache research result"""
        # Cache in SQLite
        await self.sqlite_cache.set(
            key=cache_key,
            value=json.dumps(result),
            ttl=settings.cache_ttl
        )

        # Cache semantically
        await self.vector_cache.store(cache_key, result)

    def _create_empty_summary(self) -> Dict:
        """Create empty summary when no content is available"""
        return {
            "summary": "No content could be extracted from the search results.",
            "sections": {
                "Overview": "Unable to generate summary due to content extraction issues."
            },
            "sources": [],
            "generated_at": datetime.now(),
            "word_count": 0,
            "model_used": "none",
            "provider": "none",
            "cost": 0.0
        }