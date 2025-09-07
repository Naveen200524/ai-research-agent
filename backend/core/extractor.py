import asyncio
import aiohttp
from typing import Dict, List, Optional
import trafilatura
from playwright.async_api import async_playwright
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

class ContentExtractor:
    """Extract content from web pages with fallback strategies"""
    
    def __init__(self):
        self.session = None
        self.playwright = None
        self.browser = None
        
    async def initialize(self):
        """Initialize resources"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def extract(self, url: str) -> Dict:
        """
        Extract content from URL with multiple strategies
        
        Args:
            url: URL to extract content from
            
        Returns:
            Dict with extracted content and metadata
        """
        try:
            # Try trafilatura first (fastest)
            content = await self._extract_trafilatura(url)
            
            # If content is too short, try playwright
            if not content.get("success") or len(content.get("text", "")) < 500:
                content = await self._extract_playwright(url)
            
            return content
            
        except Exception as e:
            logger.error(f"Extraction error for {url}: {e}")
            return {
                "url": url,
                "title": "",
                "text": "",
                "error": str(e),
                "success": False
            }
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def _extract_trafilatura(self, url: str) -> Dict:
        """Fast extraction using trafilatura"""
        if not self.session:
            await self.initialize()
        
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            
            html = await response.text()
            
            # Extract with trafilatura
            text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                include_images=False,
                favor_precision=True,
                deduplicate=True
            )
            
            # Extract metadata
            metadata = trafilatura.extract_metadata(html)
            
            return {
                "url": url,
                "title": metadata.title if metadata else "",
                "text": text or "",
                "author": metadata.author if metadata else "",
                "date": metadata.date if metadata else "",
                "success": bool(text)
            }
    
    async def _extract_playwright(self, url: str) -> Dict:
        """Extract from JavaScript-heavy sites using Playwright"""
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
        
        page = await self.browser.new_page()
        
        try:
            # Navigate with timeout
            await page.goto(url, wait_until="networkidle", timeout=20000)
            
            # Wait for content to load
            await page.wait_for_timeout(2000)
            
            # Extract title
            title = await page.title()
            
            # Extract main content
            text = await page.evaluate("""
                () => {
                    // Remove script and style elements
                    const scripts = document.querySelectorAll('script, style, noscript');
                    scripts.forEach(el => el.remove());
                    
                    // Try to find main content
                    const selectors = [
                        'main', 'article', '[role="main"]', 
                        '#content', '.content', '.post', '.entry-content'
                    ];
                    
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element && element.innerText.length > 100) {
                            return element.innerText;
                        }
                    }
                    
                    // Fallback to body
                    return document.body.innerText;
                }
            """)
            
            return {
                "url": url,
                "title": title,
                "text": text,
                "success": bool(text)
            }
            
        finally:
            await page.close()
    
    async def extract_batch(
        self, 
        urls: List[str], 
        max_concurrent: int = 5
    ) -> List[Dict]:
        """
        Extract content from multiple URLs concurrently
        
        Args:
            urls: List of URLs to extract
            max_concurrent: Maximum concurrent extractions
            
        Returns:
            List of extraction results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_semaphore(url):
            async with semaphore:
                return await self.extract(url)
        
        tasks = [extract_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                processed_results.append({
                    "url": url,
                    "title": "",
                    "text": "",
                    "error": str(result),
                    "success": False
                })
            else:
                processed_results.append(result)
        
        return processed_results