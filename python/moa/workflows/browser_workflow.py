"""
browser_workflow.py
Browser Workflow - Searches and summarizes results with LLM
"""

from .base_workflow import BaseWorkflow


class BrowserWorkflow(BaseWorkflow):
    """Workflow for browser/search operations with LLM summarization."""

    async def run(self, **kwargs) -> dict:
        """Run browser workflow."""
        query = kwargs.get("query", "")
        url = kwargs.get("url", "")
        
        # Fetch URL
        if url:
            print(f"🌐 Fetching: {url}")
            result = await self.orchestrator.run_capability(
                "fetch",
                {"url": url}
            )
            
            if hasattr(result, 'data'):
                return result.data
            return result
        
        # Search
        if query:
            print(f"🔍 Searching for: {query}")
            result = await self.orchestrator.run_capability(
                "search",
                {"query": query, "max_results": 5}
            )
            
            if hasattr(result, 'data'):
                data = result.data
            else:
                data = result
            
            # If we got results, summarize with LLM
            if data and data.get("results"):
                results = data["results"][:5]
                
                # Build context from search results
                context = ""
                for i, r in enumerate(results, 1):
                    title = r.get("title", "Untitled")
                    snippet = r.get("snippet", "")
                    url = r.get("url", "")
                    context += f"""
Result {i}:
Title: {title}
Snippet: {snippet}
URL: {url}

"""
                
                # Build the summarization prompt with search results
                summary_prompt = f"""You are JARVIS, an AI assistant that provides accurate information based ONLY on the search results provided below.

IMPORTANT: 
- Use ONLY the information from the search results.
- Do NOT use your own knowledge or training data.
- If the answer is not in the search results, say "I couldn't find information about that in the search results."
- Be concise and factual.

Search Results:
{context}

Question:
{query}

Answer based ONLY on the search results above:"""

                # Get LLM summary
                print("🧠 Summarizing search results...")
                summary_result = await self.orchestrator.run_capability(
                    "think",
                    {"query": summary_prompt}
                )
                
                if hasattr(summary_result, 'data'):
                    summary_data = summary_result.data
                    if summary_data and summary_data.get("response"):
                        return {
                            "success": True,
                            "answer": summary_data["response"],
                            "results": results,
                            "source": "search_with_summary",
                            "query": query
                        }
            
            # If no results or summarization failed
            if data:
                return {
                    "success": True,
                    "results": data.get("results", []),
                    "total_found": data.get("total_found", 0),
                    "source": data.get("source", "unknown"),
                    "query": query
                }
            
            return {"success": False, "error": "No search results found", "query": query}
        
        return {"success": False, "error": "No query or URL provided"}