"""
agents/browser/automation.py
Browser Automation - Control Chrome/Edge with Playwright
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("jarvis.browser_automation")


class BrowserAutomation:
    """
    Browser automation using Playwright.
    Controls Chrome, Edge, Firefox.
    """
    
    def __init__(self):
        self.browser = None
        self.page = None
        self._playwright = None
        self._initialized = False
        
        logger.info("Browser Automation initialized")
    
    async def init(self, headless: bool = False):
        """Initialize browser."""
        try:
            from playwright.async_api import async_playwright
            
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.page = await self.browser.new_page()
            self._initialized = True
            logger.info("✅ Browser automation initialized")
            return True
        except ImportError:
            logger.error("❌ Playwright not installed. Run: pip install playwright && playwright install")
            return False
        except Exception as e:
            logger.error(f"❌ Browser init error: {e}")
            return False
    
    async def goto(self, url: str, wait_load: bool = True) -> Dict:
        """Navigate to a URL."""
        if not self._initialized:
            await self.init()
        
        try:
            await self.page.goto(url, wait_until="networkidle" if wait_load else "load")
            title = await self.page.title()
            url_current = self.page.url
            return {
                "success": True,
                "url": url_current,
                "title": title
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def search(self, query: str, engine: str = "google") -> Dict:
        """Search on Google/Bing."""
        if not self._initialized:
            await self.init()
        
        try:
            if engine == "google":
                await self.goto("https://www.google.com")
                await self.page.fill('input[name="q"]', query)
                await self.page.press('input[name="q"]', "Enter")
            elif engine == "bing":
                await self.goto("https://www.bing.com")
                await self.page.fill('input[name="q"]', query)
                await self.page.press('input[name="q"]', "Enter")
            else:
                return {"success": False, "error": f"Unknown engine: {engine}"}
            
            await self.page.wait_for_load_state("networkidle")
            
            # Get results
            results = []
            if engine == "google":
                elements = await self.page.query_selector_all('div.g')
                for el in elements[:5]:
                    title_el = await el.query_selector('h3')
                    link_el = await el.query_selector('a')
                    if title_el and link_el:
                        title = await title_el.text_content()
                        link = await link_el.get_attribute('href')
                        results.append({"title": title, "link": link})
            
            return {
                "success": True,
                "query": query,
                "engine": engine,
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def click(self, selector: str) -> Dict:
        """Click an element."""
        try:
            await self.page.click(selector)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def type_text(self, selector: str, text: str) -> Dict:
        """Type text into an element."""
        try:
            await self.page.fill(selector, text)
            return {"success": True, "selector": selector, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def screenshot(self, path: str = None) -> Dict:
        """Take screenshot of current page."""
        try:
            if not path:
                from datetime import datetime
                path = f"screenshot_browser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self.page.screenshot(path=path, full_page=True)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False
        logger.info("Browser closed")