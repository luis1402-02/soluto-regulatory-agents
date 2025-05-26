"""Browser automation tool for agents."""

import asyncio
import time
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Browser, Page

from ..utils import get_logger
from .base import BaseTool, ToolResult

logger = get_logger(__name__)


class BrowserTool(BaseTool):
    """Tool for browser automation and web scraping."""

    name = "browser"
    description = "Automate browser interactions and scrape web content"

    def __init__(self):
        """Initialize browser tool."""
        self.browser: Optional[Browser] = None
        self.playwright = None

    async def initialize(self) -> None:
        """Initialize browser instance."""
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            logger.info("browser_initialized")

    async def cleanup(self) -> None:
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        screenshot: bool = False,
        wait_for: Optional[str] = None,
        timeout: int = 30000,
    ) -> ToolResult:
        """Execute browser action."""
        start_time = time.time()

        try:
            await self.initialize()

            if action == "navigate":
                result = await self._navigate(url, wait_for, timeout)
            elif action == "scrape":
                result = await self._scrape(url, selector, wait_for, timeout)
            elif action == "click":
                result = await self._click(selector, timeout)
            elif action == "fill":
                result = await self._fill(selector, text, timeout)
            elif action == "screenshot":
                result = await self._screenshot(url, selector, timeout)
            else:
                raise ValueError(f"Unsupported action: {action}")

            execution_time = time.time() - start_time

            logger.info(
                "browser_action_completed",
                action=action,
                url=url,
                execution_time=execution_time,
            )

            return ToolResult(
                success=True,
                output=result,
                execution_time=execution_time,
                metadata={"action": action, "url": url},
            )

        except Exception as e:
            logger.error("browser_action_failed", action=action, error=str(e), exc_info=e)
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _navigate(
        self,
        url: str,
        wait_for: Optional[str],
        timeout: int,
    ) -> Dict[str, Any]:
        """Navigate to URL."""
        page = await self.browser.new_page()
        
        try:
            response = await page.goto(url, timeout=timeout)
            
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout)

            title = await page.title()
            html = await page.content()

            return {
                "url": page.url,
                "title": title,
                "status": response.status if response else None,
                "html_length": len(html),
            }
        finally:
            await page.close()

    async def _scrape(
        self,
        url: str,
        selector: Optional[str],
        wait_for: Optional[str],
        timeout: int,
    ) -> Dict[str, Any]:
        """Scrape content from page."""
        page = await self.browser.new_page()
        
        try:
            await page.goto(url, timeout=timeout)
            
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout)

            if selector:
                # Scrape specific elements
                elements = await page.query_selector_all(selector)
                content = []
                
                for element in elements:
                    text = await element.text_content()
                    if text:
                        content.append(text.strip())
                
                return {
                    "url": page.url,
                    "selector": selector,
                    "count": len(content),
                    "content": content,
                }
            else:
                # Get full page content
                text = await page.text_content("body")
                html = await page.content()
                
                return {
                    "url": page.url,
                    "text": text,
                    "html": html,
                }
        finally:
            await page.close()

    async def _click(self, selector: str, timeout: int) -> Dict[str, Any]:
        """Click an element."""
        pages = self.browser.contexts[0].pages if self.browser.contexts else []
        if not pages:
            raise ValueError("No active page found")
        
        page = pages[-1]
        await page.click(selector, timeout=timeout)
        
        return {
            "selector": selector,
            "url": page.url,
        }

    async def _fill(self, selector: str, text: str, timeout: int) -> Dict[str, Any]:
        """Fill a form field."""
        pages = self.browser.contexts[0].pages if self.browser.contexts else []
        if not pages:
            raise ValueError("No active page found")
        
        page = pages[-1]
        await page.fill(selector, text, timeout=timeout)
        
        return {
            "selector": selector,
            "text": text,
            "url": page.url,
        }

    async def _screenshot(
        self,
        url: Optional[str],
        selector: Optional[str],
        timeout: int,
    ) -> Dict[str, Any]:
        """Take a screenshot."""
        page = await self.browser.new_page()
        
        try:
            if url:
                await page.goto(url, timeout=timeout)

            screenshot_options = {"full_page": True}
            
            if selector:
                element = await page.query_selector(selector)
                if element:
                    screenshot_data = await element.screenshot()
                else:
                    raise ValueError(f"Element not found: {selector}")
            else:
                screenshot_data = await page.screenshot(**screenshot_options)

            return {
                "url": page.url if url else None,
                "selector": selector,
                "screenshot": screenshot_data,
                "size": len(screenshot_data),
            }
        finally:
            await page.close()

    def get_schema(self) -> Dict[str, Any]:
        """Get tool parameter schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "scrape", "click", "fill", "screenshot"],
                    "description": "Browser action to perform",
                },
                "url": {
                    "type": "string",
                    "description": "URL to navigate to",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for element",
                },
                "text": {
                    "type": "string",
                    "description": "Text to fill in form field",
                },
                "screenshot": {
                    "type": "boolean",
                    "description": "Whether to take a screenshot",
                    "default": False,
                },
                "wait_for": {
                    "type": "string",
                    "description": "Selector to wait for before proceeding",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in milliseconds",
                    "default": 30000,
                },
            },
            "required": ["action"],
        }