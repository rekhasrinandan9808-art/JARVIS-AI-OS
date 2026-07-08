"""
agents/search/agent.py
Search Agent - Performs web searches using Tavily API
"""

import os
import logging
from typing import Dict, Any, List, Optional

from agents.base_agent import BaseAgent, AgentCapability, AgentResult

logger = logging.getLogger("jarvis.search_agent")


class SearchAgent(BaseAgent):
    """Agent for performing web searches."""
    
    name = "search"
    description = "Performs web searches using Tavily API"
    agent_id = 40
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.serper_key = os.getenv("SERPER_API_KEY", "")
        self.client = None
        
        # Try Tavily first
        if self.api_key:
            try:
                from tavily import TavilyClient
                self.client = TavilyClient(api_key=self.api_key)
                logger.info("✅ SearchAgent: Tavily API initialized")
            except ImportError:
                logger.warning("⚠️ SearchAgent: tavily-python not installed. Run: pip install tavily-python")
            except Exception as e:
                logger.error(f"❌ SearchAgent: Failed to initialize Tavily: {e}")
        
        # If Tavily not available, try Serper
        if not self.client and self.serper_key:
            logger.info("✅ SearchAgent: Serper API available as fallback")
    
    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("search", "Search the web for information", {
                "query": {"type": "string", "required": True},
                "max_results": {"type": "integer", "default": 5}
            }),
            AgentCapability("search_news", "Search for news articles", {
                "query": {"type": "string", "required": True}
            }),
        ]
    
    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute search action."""
        logger.info(f"SearchAgent: {action} with params: {params}")
        
        if action == "search":
            return self._search(params)
        
        if action == "search_news":
            return self._search_news(params)
        
        return {
            "success": False,
            "error": f"Unknown action: {action}"
        }
    
    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a web search."""
        query = params.get("query", "")
        max_results = params.get("max_results", 5)
        
        if not query:
            return {
                "success": False,
                "error": "No search query provided",
                "answer": "Please provide a search query."
            }
        
        # Try Tavily
        if self.client:
            try:
                response = self.client.search(
                    query=query,
                    max_results=max_results,
                    include_answer=True,
                    include_raw_content=False
                )
                
                results = []
                for result in response.get("results", []):
                    results.append({
                        "title": result.get("title", "No title"),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0)
                    })
                
                answer = response.get("answer", "")
                if not answer and results:
                    first_result = results[0]
                    answer = f"Found information about '{query}'. The top result is: {first_result['title']}"
                    if first_result.get('content'):
                        answer += f" - {first_result['content'][:200]}..."
                
                return {
                    "success": True,
                    "answer": answer or f"Found {len(results)} results for '{query}'.",
                    "query": query,
                    "results": results,
                    "result_count": len(results)
                }
            except Exception as e:
                logger.error(f"Tavily search error: {e}")
                # Fall through to Serper
        
        # Try Serper as fallback
        if self.serper_key:
            try:
                import requests
                headers = {
                    'X-API-KEY': self.serper_key,
                    'Content-Type': 'application/json'
                }
                payload = {'q': query, 'num': max_results}
                response = requests.post('https://google.serper.dev/search', headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for item in data.get("organic", [])[:max_results]:
                        results.append({
                            "title": item.get("title", "No title"),
                            "url": item.get("link", ""),
                            "content": item.get("snippet", ""),
                            "score": 1.0
                        })
                    
                    answer = f"Found {len(results)} results for '{query}'."
                    if results:
                        answer = f"Top result: {results[0]['title']} - {results[0]['content'][:150]}..."
                    
                    return {
                        "success": True,
                        "answer": answer,
                        "query": query,
                        "results": results,
                        "result_count": len(results)
                    }
            except Exception as e:
                logger.error(f"Serper search error: {e}")
        
        # No API available
        return {
            "success": False,
            "error": "No search API configured",
            "answer": f"Search is not configured. Please add TAVILY_API_KEY or SERPER_API_KEY to .env file.",
            "query": query
        }
    
    def _search_news(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for news articles."""
        query = params.get("query", "")
        
        if not query:
            return {
                "success": False,
                "error": "No search query provided"
            }
        
        # Use search with news context
        result = self._search({"query": f"news {query}", "max_results": 5})
        
        if result.get("success"):
            result["answer"] = f"News results for '{query}':\n" + result.get("answer", "")
        
        return result