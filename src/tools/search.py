"""Web search tool for agents."""

import asyncio
import time
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from ..config import get_settings
from ..utils import get_logger
from .base import BaseTool, ToolResult

logger = get_logger(__name__)


class WebSearchTool(BaseTool):
    """Tool for searching the web."""

    name = "web_search"
    description = "Search the web for information"

    def __init__(self):
        """Initialize web search tool."""
        self.settings = get_settings()

    async def execute(
        self,
        query: str,
        num_results: int = 10,
        search_engine: str = "duckduckgo",
    ) -> ToolResult:
        """Execute web search."""
        start_time = time.time()

        try:
            if search_engine == "duckduckgo":
                results = await self._search_duckduckgo(query, num_results)
            else:
                raise ValueError(f"Unsupported search engine: {search_engine}")

            execution_time = time.time() - start_time

            logger.info(
                "web_search_completed",
                query=query,
                results_count=len(results),
                execution_time=execution_time,
            )

            return ToolResult(
                success=True,
                output=results,
                execution_time=execution_time,
                metadata={
                    "query": query,
                    "search_engine": search_engine,
                    "results_count": len(results),
                },
            )

        except Exception as e:
            logger.error("web_search_failed", query=query, error=str(e), exc_info=e)
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _search_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo HTML interface."""
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=params) as response:
                html = await response.text()

        # Parse results
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for result in soup.find_all("div", class_="result", limit=num_results):
            title_elem = result.find("a", class_="result__a")
            snippet_elem = result.find("a", class_="result__snippet")
            
            if title_elem:
                title = title_elem.get_text(strip=True)
                link = title_elem.get("href", "")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                # Clean up the link
                if link.startswith("//duckduckgo.com/l/?"):
                    # Extract actual URL from DDG redirect
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                    if "uddg" in parsed:
                        link = parsed["uddg"][0]

                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                })

        return results

    async def search_and_extract(
        self,
        query: str,
        extract_content: bool = True,
        num_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search and optionally extract content from results."""
        # First, perform the search
        search_result = await self.execute(query, num_results)
        
        if not search_result.success:
            return []

        results = search_result.output

        if not extract_content:
            return results

        # Extract content from each result
        enriched_results = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for result in results:
                task = self._extract_page_content(session, result)
                tasks.append(task)
            
            enriched = await asyncio.gather(*tasks, return_exceptions=True)
            
            for original, enhanced in zip(results, enriched):
                if isinstance(enhanced, Exception):
                    logger.warning(
                        "content_extraction_failed",
                        url=original["link"],
                        error=str(enhanced),
                    )
                    enriched_results.append(original)
                else:
                    enriched_results.append(enhanced)

        return enriched_results

    async def _extract_page_content(
        self,
        session: aiohttp.ClientSession,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract content from a web page."""
        try:
            async with session.get(
                result["link"],
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "Mozilla/5.0 (compatible; SolutoBot/1.0)"},
            ) as response:
                if response.status != 200:
                    return result

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Extract text
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = " ".join(chunk for chunk in chunks if chunk)

                # Limit content length
                max_length = 1000
                if len(text) > max_length:
                    text = text[:max_length] + "..."

                result["content"] = text
                return result

        except Exception as e:
            logger.debug("content_extraction_error", url=result["link"], error=str(e))
            return result

    def get_schema(self) -> Dict[str, Any]:
        """Get tool parameter schema."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
                "search_engine": {
                    "type": "string",
                    "enum": ["duckduckgo"],
                    "description": "Search engine to use",
                    "default": "duckduckgo",
                },
            },
            "required": ["query"],
        }