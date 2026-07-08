"""
browser/agent.py
Agent #8: BrowserAgent -- fetches web pages and runs real-time web search using Tavily API.
"""

from __future__ import annotations
import re
import urllib.parse
import urllib.request
import asyncio
import logging
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent, AgentCapability

# Force load .env file
try:
    from dotenv import load_dotenv
    possible_paths = [
        Path(__file__).parent.parent.parent / ".env",
        Path(__file__).parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in possible_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded .env from {env_path}")
            break
except ImportError:
    print("⚠️ python-dotenv not installed. Install with: pip install python-dotenv")

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    print("⚠️ aiohttp not installed. Install with: pip install aiohttp")

logger = logging.getLogger("jarvis.browser")


class BrowserAgent(BaseAgent):
    name = "browser"
    description = "Fetches web pages and runs real-time web search using Tavily API."
    agent_id = 8

    def __init__(self):
        super().__init__()
        self.TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
        self.SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
        
        if self.TAVILY_API_KEY:
            print(f"✅ BrowserAgent: Tavily API key loaded ({self.TAVILY_API_KEY[:8]}...)")
        else:
            print("⚠️ BrowserAgent: Tavily API key NOT found.")

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("fetch", "Fetch a URL and return stripped text", {"url": "str"}),
            AgentCapability("search", "Real-time web search using Tavily API", {"query": "str", "max_results": "int (default 5)"}),
        ]

    def _get(self, url: str, timeout: int = 15) -> str:
        """Synchronous HTTP GET request."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch {url}: {e}")

    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML."""
        title = ""
        m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
        return title

    def _clean_html(self, html: str) -> str:
        """Clean HTML by removing scripts, styles, and tags."""
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def _search_tavily(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search using Tavily API - includes answer field.
        """
        if not self.TAVILY_API_KEY:
            logger.warning("Tavily API key not configured")
            return {"answer": "", "results": []}
        
        if not HAS_AIOHTTP:
            logger.warning("aiohttp required for Tavily API")
            return {"answer": "", "results": []}
        
        results = []
        answer = ""
        url = "https://api.tavily.com/search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": self.TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
            "include_raw_content": False,
            "search_depth": "basic",  # Use "advanced" for more thorough search
        }
        
        try:
            logger.info(f"📡 Calling Tavily API for: {query[:50]}...")
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        answer = data.get("answer", "")
                        logger.info(f"✅ Tavily returned {len(results)} results")
                        if answer:
                            logger.info(f"📝 Tavily answer: {answer[:100]}...")
                    else:
                        error_text = await response.text()
                        logger.error(f"Tavily API error {response.status}: {error_text[:200]}")
                        
        except asyncio.TimeoutError:
            logger.warning("Tavily API timeout")
            return {"answer": "", "results": [], "timeout": True}
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
        
        formatted_results = []
        for r in results:
            formatted_results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
                "score": r.get("score", 0),
                "engine": "tavily"
            })
        
        return {
            "answer": answer,
            "results": formatted_results,
            "timeout": False
        }

    async def _search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Fallback: Search using DuckDuckGo (scraping)."""
        logger.info("🦆 Using DuckDuckGo fallback...")
        url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        
        try:
            raw = await asyncio.to_thread(self._get, url, 15)
            
            if "captcha" in raw.lower() or "anomaly" in raw.lower():
                logger.warning("DuckDuckGo returned CAPTCHA")
                return []
            
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(raw, "lxml")
                results = []
                
                result_elements = soup.select(".result")
                if not result_elements:
                    result_elements = soup.select(".web-result")
                
                for elem in result_elements[:max_results]:
                    link = elem.select_one("a.result__a") or elem.select_one("a")
                    if link:
                        href = link.get("href", "")
                        if href.startswith("/"):
                            href = "https://duckduckgo.com" + href
                        title = link.get_text(strip=True)
                        
                        snippet = ""
                        snippet_elem = elem.select_one(".result__snippet")
                        if snippet_elem:
                            snippet = snippet_elem.get_text(strip=True)
                        
                        if title and href:
                            results.append({
                                "title": title[:200],
                                "url": href,
                                "snippet": snippet[:300] if snippet else "",
                                "engine": "duckduckgo"
                            })
                
                logger.info(f"🦆 DuckDuckGo found {len(results)} results")
                return results
            except ImportError:
                pass
                
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
        
        return []

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "fetch":
            url = params["url"]
            timeout = params.get("timeout", 15)
            
            if not url.startswith(("http://", "https://")):
                raise ValueError("URL must start with http:// or https://")
            
            raw = await asyncio.to_thread(self._get, url, timeout)
            title = self._extract_title(raw)
            text = self._clean_html(raw)
            
            return {
                "url": url,
                "title": title,
                "text": text[:5000]
            }

        if action == "search":
            query = params["query"]
            max_results = int(params.get("max_results", 5))
            
            logger.info(f"🔍 Searching for: {query}")
            
            results = []
            source = "none"
            answer = ""
            tavily_timeout = False
            
            # Try Tavily first
            if self.TAVILY_API_KEY:
                tavily_result = await self._search_tavily(query, max_results)
                results = tavily_result.get("results", [])
                answer = tavily_result.get("answer", "")
                tavily_timeout = tavily_result.get("timeout", False)
                
                if results:
                    source = "tavily"
                    logger.info(f"✅ Tavily found {len(results)} results")
            
            # Fallback to DuckDuckGo if Tavily failed or timed out
            if not results:
                if tavily_timeout:
                    logger.info("⏳ Tavily timed out, falling back to DuckDuckGo...")
                results = await self._search_duckduckgo(query, max_results)
                if results:
                    source = "duckduckgo"
            
            if not results:
                logger.warning("No search results found")
                return {
                    "query": query,
                    "results": [],
                    "total_found": 0,
                    "source": "none",
                    "answer": ""
                }
            
            return {
                "query": query,
                "results": results,
                "total_found": len(results),
                "source": source,
                "answer": answer
            }