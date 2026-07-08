"""
research_workflow.py
Research Workflow - Orchestrates the complete research process using multiple capabilities
"""

import asyncio
import time
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from .base_workflow import BaseWorkflow


class ResearchWorkflow(BaseWorkflow):
    """
    Research workflow that orchestrates the complete research process.
    Uses the orchestrator to find and execute capabilities.
    
    Flow:
    1. Check memory cache first (avoid redundant work)
    2. plan - Create a research plan
    3. extract_keywords - Extract keywords from the plan
    4. search - Search for information (main topic + sub-questions)
    5. verify_sources - Remove duplicates and invalid sources
    6. rank_sources - Rank sources BEFORE fetching (saves bandwidth)
    7. fetch - Download top N full webpage content (concurrently with rate limiting)
    8. summarize - Summarize the full webpage content
    9. store - Save to memory for future retrieval
    """

    # Configuration
    MAX_SOURCES_TO_FETCH = 5
    FETCH_TIMEOUT = 10  # seconds per fetch
    MAX_SOURCES_TO_SEARCH = 10
    MAX_CONCURRENT_FETCHES = 5
    MAX_CONCURRENT_WORKFLOWS = 3
    ENABLE_CACHE = True
    CACHE_TTL_SECONDS = 3600  # 1 hour
    
    # Cache to prevent stampede
    _research_locks: Dict[str, asyncio.Lock] = {}
    _lock = asyncio.Lock()  # For managing the locks dict

    async def run(self, topic: str) -> dict:
        """
        Run the research workflow for a given topic.
        
        Args:
            topic: The research topic
            
        Returns:
            dict: Complete research results with all steps
        """
        print(f"[Workflow] 🧠 Researching: {topic}")
        print("-" * 50)

        # FIX #3: Prevent cache stampede with per-topic lock
        lock = await self._get_lock(topic)
        
        async with lock:
            # ========== STEP 0: CHECK CACHE ==========
            memory_key = self._normalize_key(topic)
            
            if self.ENABLE_CACHE:
                print("[Workflow] 💾 Checking memory cache...")
                cache_result = await self.orchestrator.run_capability(
                    "get",
                    {"key": memory_key}
                )
                
                if not self._is_error(cache_result):
                    cached_data = self._extract_data(cache_result)
                    if cached_data:
                        cached_time = cached_data.get("timestamp", 0)
                        current_time = time.time()
                        age = current_time - cached_time
                        
                        if age < self.CACHE_TTL_SECONDS:
                            print(f"[Workflow] ✅ Found fresh cache ({age:.0f}s old), returning cached result")
                            return {
                                "success": True,
                                "topic": topic,
                                "from_cache": True,
                                "cache_age": age,
                                "summary": cached_data.get("summary", ""),
                                "source_count": cached_data.get("source_count", 0),
                                "keywords": cached_data.get("keywords", []),
                                "urls": cached_data.get("urls", []),
                                "sources": cached_data.get("sources", []),
                                "memory_key": memory_key,
                                "metadata": {
                                    "cached": True,
                                    "cache_age_seconds": age
                                }
                            }
                        else:
                            print(f"[Workflow] ⚠️ Cache expired ({age:.0f}s old), refreshing...")

            # ========== STEP 1: PLAN ==========
            print("[Workflow] 📋 Creating research plan...")
            plan_result = await self.orchestrator.run_capability(
                "plan",
                {"topic": topic}
            )

            if self._is_error(plan_result):
                return self._format_error(plan_result, "planning")

            plan_data = self._extract_data(plan_result)
            sub_questions = plan_data.get("sub_questions", [])
            print(f"[Workflow] ✅ Plan created with {len(sub_questions)} sub-questions")
            
            # ========== STEP 2: EXTRACT KEYWORDS ==========
            print("[Workflow] 🔑 Extracting keywords...")
            
            plan_text = f"{topic} " + " ".join(sub_questions)
            
            keyword_result = await self.orchestrator.run_capability(
                "extract_keywords",
                {"text": plan_text}
            )

            if self._is_error(keyword_result):
                keywords = []
                print("[Workflow] ⚠️ Keyword extraction failed, continuing...")
            else:
                keyword_data = self._extract_data(keyword_result)
                if isinstance(keyword_data, dict):
                    keywords = keyword_data.get("keywords", [])
                else:
                    keywords = keyword_data if isinstance(keyword_data, list) else []
                
                topic_lower = topic.lower()
                keywords = [
                    k for k in keywords 
                    if k.lower() not in topic_lower and len(k) > 2
                ]
                print(f"[Workflow] ✅ Extracted {len(keywords)} keywords")

            # ========== STEP 3: SEARCH (Main + Sub-questions) ==========
            print("[Workflow] 🔍 Searching...")
            
            # FIX #7: Search main topic AND sub-questions
            search_queries = [topic]
            
            # Add sub-questions as search queries (limit to 3)
            if sub_questions:
                for sq in sub_questions[:3]:
                    # Clean the sub-question for search
                    clean_sq = re.sub(r'^what|who|how|why|when|where\s+', '', sq, flags=re.I)
                    clean_sq = re.sub(r'[?]', '', clean_sq).strip()
                    if len(clean_sq) > 10:
                        search_queries.append(clean_sq)
            
            # Add keyword-based query if available
            if keywords:
                keyword_query = f"{topic} {' '.join(keywords[:3])}"
                if keyword_query not in search_queries:
                    search_queries.append(keyword_query)
            
            print(f"[Workflow] 📍 Running {len(search_queries)} searches...")
            
            # Execute all searches concurrently
            search_tasks = [
                self.orchestrator.run_capability(
                    "search",
                    {"query": q, "max_results": self.MAX_SOURCES_TO_SEARCH // len(search_queries) + 2}
                )
                for q in search_queries
            ]
            
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Merge all search results
            all_sources = []
            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    print(f"[Workflow] ⚠️ Search '{search_queries[i]}' failed: {str(result)[:50]}")
                    continue
                if self._is_error(result):
                    continue
                search_data = self._extract_data(result)
                sources = self._extract_sources(search_data)
                all_sources.extend(sources)
            
            print(f"[Workflow] ✅ Found {len(all_sources)} total sources")

            # ========== STEP 4: VERIFY SOURCES ==========
            print("[Workflow] 🔍 Verifying sources (removing duplicates)...")
            
            verify_result = await self.orchestrator.run_capability(
                "verify_sources",
                {"results": all_sources}
            )

            if self._is_error(verify_result):
                verified_sources = all_sources
                duplicates_removed = 0
                print("[Workflow] ⚠️ Source verification failed")
            else:
                verify_data = self._extract_data(verify_result)
                if isinstance(verify_data, dict):
                    verified_sources = verify_data.get("verified_sources", all_sources)
                    duplicates_removed = verify_data.get("duplicates_removed", 0)
                else:
                    verified_sources = verify_data if isinstance(verify_data, list) else all_sources
                    duplicates_removed = 0
                print(f"[Workflow] ✅ Verified {len(verified_sources)} sources ({duplicates_removed} duplicates removed)")

            # ========== STEP 5: RANK SOURCES ==========
            print("[Workflow] 📊 Ranking sources by relevance...")
            
            rank_result = await self.orchestrator.run_capability(
                "rank_sources",
                {"results": verified_sources, "topic": topic}
            )

            if self._is_error(rank_result):
                ranked_sources = verified_sources
                print("[Workflow] ⚠️ Source ranking failed")
            else:
                rank_data = self._extract_data(rank_result)
                if isinstance(rank_data, dict):
                    ranked_sources = rank_data.get("ranked_sources", verified_sources)
                else:
                    ranked_sources = rank_data if isinstance(rank_data, list) else verified_sources
                print(f"[Workflow] ✅ Sources ranked")

            # ========== STEP 6: FETCH TOP N PAGES ==========
            sources_to_fetch = ranked_sources[:self.MAX_SOURCES_TO_FETCH]
            print(f"[Workflow] 🌐 Fetching {len(sources_to_fetch)} full pages concurrently...")
            
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_FETCHES)
            
            async def fetch_with_semaphore(url, timeout):
                async with semaphore:
                    # FIX #1: Proper timeout handling - BrowserAgent should implement
                    return await self.orchestrator.run_capability(
                        "fetch",
                        {"url": url, "timeout": timeout}
                    )
            
            fetch_tasks = []
            fetch_urls = []
            for source in sources_to_fetch:
                url = source.get("url")
                if url and url.startswith(("http://", "https://")):
                    fetch_tasks.append(
                        fetch_with_semaphore(url, self.FETCH_TIMEOUT)
                    )
                    fetch_urls.append(url)
            
            if fetch_tasks:
                fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                
                fetched_pages = []
                for i, fetch_result in enumerate(fetch_results):
                    url = fetch_urls[i]
                    
                    # FIX #2: Only retry network errors
                    if isinstance(fetch_result, Exception):
                        if self._is_network_error(fetch_result):
                            print(f"[Workflow] ⚠️ Network error for {url}, retrying...")
                            retry_result = await fetch_with_semaphore(url, self.FETCH_TIMEOUT)
                            if isinstance(retry_result, Exception) and self._is_network_error(retry_result):
                                print(f"[Workflow] ❌ Retry failed for {url}: {str(retry_result)[:50]}")
                                continue
                            elif self._is_error(retry_result):
                                continue
                            else:
                                fetch_result = retry_result
                        else:
                            print(f"[Workflow] ❌ Non-network error for {url}: {str(fetch_result)[:50]}")
                            continue
                    
                    if self._is_error(fetch_result):
                        print(f"[Workflow] ❌ Failed to fetch {url}")
                        continue
                    
                    page_data = self._extract_data(fetch_result)
                    
                    title = page_data.get("title")
                    if not title or title == "Untitled":
                        for source in sources_to_fetch:
                            if source.get("url") == url:
                                title = source.get("title", "Untitled")
                                break
                    
                    fetched_pages.append({
                        "url": page_data.get("url", url),
                        "title": title or "Untitled",
                        "text": page_data.get("text", ""),
                        "snippet": next((s.get("snippet", "") for s in sources_to_fetch if s.get("url") == url), "")
                    })
                
                print(f"[Workflow] ✅ Successfully fetched {len(fetched_pages)} full pages")
            else:
                fetched_pages = []
                print("[Workflow] ⚠️ No fetchable URLs found")

            # ========== STEP 7: SUMMARIZE ==========
            print("[Workflow] 📝 Summarizing findings...")
            
            documents = []
            for source in fetched_pages:
                if isinstance(source, dict):
                    text_content = source.get("text", "")
                    if text_content and len(text_content) > 100:
                        documents.append({
                            "title": source.get("title", "Untitled"),
                            "text": text_content,
                            "url": source.get("url", "")
                        })
            
            if not documents:
                print("[Workflow] ⚠️ No full page content available, using snippets")
                for source in sources_to_fetch[:3]:
                    if isinstance(source, dict):
                        documents.append({
                            "title": source.get("title", "Untitled"),
                            "text": source.get("snippet", source.get("text", "")),
                            "url": source.get("url", "")
                        })

            if documents:
                summary_result = await self.orchestrator.run_capability(
                    "summarize",
                    {"documents": documents}
                )

                if self._is_error(summary_result):
                    return self._format_error(summary_result, "summarizing", {
                        "plan": plan_data,
                        "keywords": keywords
                    })

                summary_data = self._extract_data(summary_result)
            else:
                summary_data = {
                    "summary": "No content available to summarize.",
                    "source_count": 0
                }

            # ========== STEP 8: STORE IN MEMORY ==========
            print("[Workflow] 💾 Storing research in memory...")
            
            memory_value = {
                "topic": topic,
                "summary": summary_data.get("summary", ""),
                "source_count": len(fetched_pages),
                "keywords": keywords,
                "urls": [p.get("url") for p in fetched_pages],
                "sources": fetched_pages,
                "timestamp": time.time(),
                "timestamp_iso": datetime.utcnow().isoformat(),
                "metadata": {
                    "total_sources_found": len(all_sources),
                    "verified_sources": len(verified_sources),
                    "pages_fetched": len(fetched_pages),
                    "duplicates_removed": duplicates_removed,
                    "keywords_extracted": len(keywords)
                }
            }
            
            store_result = await self.orchestrator.run_capability(
                "set",
                {"key": memory_key, "value": memory_value}
            )
            
            if self._is_error(store_result):
                print("[Workflow] ⚠️ Failed to store in memory")
            else:
                print(f"[Workflow] ✅ Research stored in memory (key: {memory_key})")

            print("-" * 50)
            print("[Workflow] ✅ Research complete!")
            
            return {
                "success": True,
                "topic": topic,
                "from_cache": False,
                "plan": plan_data,
                "keywords": keywords,
                "sources": fetched_pages or ranked_sources,
                "summary": summary_data.get("summary", "No summary generated"),
                "source_count": len(fetched_pages),
                "memory_key": memory_key,
                "metadata": {
                    "total_sources_found": len(all_sources),
                    "verified_sources": len(verified_sources),
                    "pages_fetched": len(fetched_pages),
                    "duplicates_removed": duplicates_removed,
                    "keywords_extracted": len(keywords)
                }
            }

    async def _get_lock(self, topic: str) -> asyncio.Lock:
        """Get or create a lock for a topic to prevent cache stampede."""
        async with self._lock:
            if topic not in self._research_locks:
                self._research_locks[topic] = asyncio.Lock()
            return self._research_locks[topic]

    def _normalize_key(self, topic: str) -> str:
        """Normalize a topic string for use as a memory key."""
        # FIX #6: Clean the topic string
        key = topic.lower().strip()
        # Remove problematic characters
        key = re.sub(r'[^a-z0-9\s\-_]', '', key)
        # Replace spaces with underscores
        key = re.sub(r'\s+', '_', key)
        return f"research/{key}"

    def _is_network_error(self, error: Exception) -> bool:
        """Check if an exception is a network error that should be retried."""
        error_str = str(error).lower()
        network_errors = [
            "timeout", "connection", "refused", "reset", 
            "broken pipe", "no route", "unreachable",
            "ssl", "certificate", "dns", "resolve"
        ]
        return any(err in error_str for err in network_errors)

    def _is_error(self, result) -> bool:
        """Check if a result is an error."""
        if hasattr(result, 'success'):
            return not result.success
        if isinstance(result, dict):
            return result.get('success') == False
        return False

    def _format_error(self, result, step: str, partial_data: dict = None) -> dict:
        """Format an error response."""
        error_msg = result.error if hasattr(result, 'error') else str(result)
        if isinstance(result, dict):
            error_msg = result.get('error', str(result))
        
        response = {
            "success": False,
            "error": f"Research failed at '{step}' step: {error_msg}",
            "step": step,
        }
        
        if partial_data:
            response.update(partial_data)
            
        return response

    def _extract_data(self, result):
        """Extract data from a result (AgentResult or dict)."""
        if hasattr(result, 'data'):
            return result.data
        return result

    def _extract_sources(self, search_data) -> list:
        """Extract sources from search data."""
        sources = []
        if isinstance(search_data, dict):
            if "results" in search_data:
                for result in search_data["results"]:
                    if isinstance(result, dict):
                        sources.append({
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "snippet": result.get("snippet", ""),
                            "text": result.get("text", result.get("snippet", ""))
                        })
            elif "url" in search_data:
                sources.append(search_data)
        elif isinstance(search_data, list):
            for item in search_data:
                if isinstance(item, dict):
                    sources.append(item)
                else:
                    sources.append({"text": str(item)})
        else:
            sources.append({"text": str(search_data)})
            
        return sources

    async def run_simple(self, topic: str) -> str:
        """Simplified version - just returns the summary as a string."""
        result = await self.run(topic)
        if result.get("success"):
            return result.get("summary", "No summary available")
        return f"Error: {result.get('error', 'Unknown error')}"

    async def run_with_details(self, topic: str, verbose: bool = True) -> dict:
        """Run research with detailed logging."""
        if verbose:
            print("\n" + "=" * 60)
            print(f"🔬 RESEARCH WORKFLOW: {topic}")
            print("=" * 60)
        
        return await self.run(topic)

    async def run_batch(self, topics: list) -> dict:
        """
        Run research on multiple topics concurrently with rate limiting.
        
        Args:
            topics: List of topics to research
            
        Returns:
            dict: Results for all topics
        """
        # FIX #8: Limit concurrent workflows
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_WORKFLOWS)
        
        async def worker(topic):
            async with semaphore:
                return await self.run(topic)
        
        tasks = [worker(topic) for topic in topics]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "topic": topics[i],
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return {
            "success": True,
            "results": processed_results,
            "total_topics": len(topics),
            "successful": sum(1 for r in processed_results if r.get("success", False))
        }