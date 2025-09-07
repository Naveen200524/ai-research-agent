import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime
from duckduckgo_search import AsyncDDGS
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

class MultiSearcher:
    """Multi-engine search with automatic fallback"""

    def __init__(self, brave_api_key: Optional[str] = None):
        self.brave_api_key = brave_api_key
        self.ddgs = AsyncDDGS()
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search(
        self,
        query: str,
        count: int = 10,
        freshness: Optional[str] = None,
        engines: List[str] = ["duckduckgo"]
    ) -> List[Dict]:
        """
        Perform web search using multiple engines

        Args:
            query: Search query
            count: Number of results
            freshness: Time filter (pd, pw, pm, py)
            engines: List of search engines to use
        """
        results = []
        tasks = []

        # Create search tasks for each engine
        if "duckduckgo" in engines:
            tasks.append(self._search_duckduckgo(query, count, freshness))

        if "brave" in engines and self.brave_api_key:
            tasks.append(self._search_brave(query, count, freshness))

        # Execute searches in parallel
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle errors
            seen_urls = set()
            for engine_results in search_results:
                if isinstance(engine_results, Exception):
                    logger.error(f"Search engine error: {engine_results}")
                    continue

                for result in engine_results:
                    if result['url'] not in seen_urls:
                        results.append(result)
                        seen_urls.add(result['url'])

        # Sort by relevance score
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        return results[:count]

    async def _search_duckduckgo(
        self,
        query: str,
        count: int,
        freshness: Optional[str]
    ) -> List[Dict]:
        """Search using DuckDuckGo with enhanced configuration"""
        try:
            # Map freshness to DuckDuckGo format
            timelimit = None
            if freshness:
                timelimit_map = {
                    'pd': 'd',  # past day
                    'pw': 'w',  # past week
                    'pm': 'm',  # past month
                    'py': 'y'   # past year
                }
                timelimit = timelimit_map.get(freshness)

            # Enhanced search configuration based on documentation
            search_params = {
                "query": query,
                "region": "wt-wt",  # Worldwide
                "timelimit": timelimit,
                "max_results": count,
                "backend": "api",  # Use API backend for better results
                "safesearch": "moderate"
            }

            # Perform search with enhanced parameters
            results = []
            async for result in self.ddgs.text(**search_params):
                # Enhanced result processing with better metadata
                result_dict = {
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "description": result.get("body", ""),
                    "snippet": result.get("body", ""),  # Additional snippet field
                    "source": "duckduckgo",
                    "relevance_score": 0.9 - (len(results) * 0.05),
                    "timestamp": datetime.now().isoformat(),
                    "engine": "duckduckgo"
                }

                # Add age information if available
                if result.get("date"):
                    result_dict["age"] = result.get("date")

                results.append(result_dict)

                # Limit results to requested count
                if len(results) >= count:
                    break

            logger.info(f"DuckDuckGo search completed: {len(results)} results for '{query}'")
            return results

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

    async def _search_brave(
        self,
        query: str,
        count: int,
        freshness: Optional[str]
    ) -> List[Dict]:
        """Search using Brave Search API"""
        if not self.brave_api_key or not self.session:
            return []

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_api_key
        }

        params = {
            "q": query,
            "count": count,
            "text_decorations": False,
            "search_lang": "en"
        }

        if freshness:
            params["freshness"] = freshness

        try:
            async with self.session.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logger.error(f"Brave API error: {response.status}")
                    return []

                data = await response.json()

                results = []
                for item in data.get("web", {}).get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                        "age": item.get("age"),
                        "source": "brave",
                        "relevance_score": item.get("relevance_score", 0.5)
                    })

                return results

        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return []

    async def search_news(
        self,
        query: str,
        count: int = 10,
        freshness: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for news articles using DuckDuckGo news backend

        Args:
            query: Search query
            count: Number of results
            freshness: Time filter (pd, pw, pm, py)
        """
        try:
            # Map freshness to DuckDuckGo format
            timelimit = None
            if freshness:
                timelimit_map = {
                    'pd': 'd',  # past day
                    'pw': 'w',  # past week
                    'pm': 'm',  # past month
                    'py': 'y'   # past year
                }
                timelimit = timelimit_map.get(freshness)

            # Use news backend for better news results
            search_params = {
                "query": query,
                "region": "wt-wt",  # Worldwide
                "timelimit": timelimit,
                "max_results": count,
                "backend": "news",  # News-specific backend
                "safesearch": "moderate"
            }

            results = []
            async for result in self.ddgs.text(**search_params):
                result_dict = {
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "description": result.get("body", ""),
                    "snippet": result.get("body", ""),
                    "source": result.get("source", "duckduckgo-news"),
                    "date": result.get("date"),
                    "relevance_score": 0.9 - (len(results) * 0.05),
                    "timestamp": datetime.now().isoformat(),
                    "engine": "duckduckgo-news",
                    "type": "news"
                }

                results.append(result_dict)

                if len(results) >= count:
                    break

            logger.info(f"DuckDuckGo news search completed: {len(results)} results for '{query}'")
            return results

        except Exception as e:
            logger.error(f"DuckDuckGo news search error: {e}")
            return []

    async def _search_brave(
        self, 
        query: str, 
        count: int,
        freshness: Optional[str]
    ) -> List[Dict]:
        """Search using Brave Search API"""
        if not self.brave_api_key or not self.session:
            return []
        
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_api_key
        }
        
        params = {
            "q": query,
            "count": count,
            "text_decorations": False,
            "search_lang": "en"
        }
        
        if freshness:
            params["freshness"] = freshness
        
        try:
            async with self.session.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logger.error(f"Brave API error: {response.status}")
                    return []
                
                data = await response.json()
                
                results = []
                for item in data.get("web", {}).get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                        "age": item.get("age"),
                        "source": "brave",
                        "relevance_score": item.get("relevance_score", 0.5)
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return []