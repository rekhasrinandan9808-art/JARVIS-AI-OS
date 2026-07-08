"""
research/agent.py
Agent #3: ResearchAgent -- plans and structures research tasks
"""

from __future__ import annotations
import re
import logging
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability

logger = logging.getLogger("jarvis.research")


class ResearchAgent(BaseAgent):
    name = "research"
    description = (
        "Breaks a research question into a structured plan of sub-questions and sources to check. "
        "Does not itself fetch the web -- wire it to the browser agent for that."
    )
    agent_id = 3

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                "plan",
                "Create a research plan",
                {"topic": "str"},
            ),
            AgentCapability(
                "summarize",
                "Summarize fetched documents",
                {"documents": "list"},
            ),
            AgentCapability(
                "extract_keywords",
                "Extract important keywords",
                {"text": "str"},
            ),
            AgentCapability(
                "rank_sources",
                "Rank search results",
                {"results": "list", "topic": "str"},
            ),
            AgentCapability(
                "verify_sources",
                "Remove duplicate or invalid sources",
                {"results": "list"},
            ),
        ]

    def _detect_topic_type(self, topic: str) -> str:
        """
        Detect the type of topic for better question generation.
        
        Args:
            topic: The research topic
            
        Returns:
            str: Topic type (person, technology, concept, event, place, organization)
        """
        topic_lower = topic.lower()
        
        # Person indicators
        person_patterns = [
            r'\b(who|mr|mrs|ms|dr|professor|sir|lord|lady)\b',
            r'\b(born|died|birth|death)\b',
            r'\b(astronaut|scientist|physicist|mathematician|engineer|inventor)\b',
            r'\b(president|prime minister|king|queen|emperor)\b',
            r'\b(artist|musician|painter|composer|writer|author|poet)\b',
            r'\b(actor|actress|director|producer|filmmaker)\b',
            r'\b(athlete|sports|player|coach|olympic)\b',
        ]
        if any(re.search(pattern, topic_lower) for pattern in person_patterns):
            return "person"
        
        # Technology indicators
        tech_keywords = [
            'ai', 'ml', 'algorithm', 'software', 'hardware', 'cloud',
            'blockchain', 'quantum', 'robot', 'cyber', 'digital', 'tech',
            'programming', 'code', 'api', 'framework', 'library', 'tool',
            'machine learning', 'deep learning', 'neural network', 'llm',
            'model', 'dataset', 'computing', 'processing', 'storage'
        ]
        if any(keyword in topic_lower for keyword in tech_keywords):
            return "technology"
        
        # Place indicators
        place_keywords = [
            'country', 'city', 'state', 'province', 'river', 'mountain',
            'island', 'continent', 'region', 'capital', 'coast', 'desert',
            'forest', 'lake', 'ocean', 'sea', 'valley', 'volcano'
        ]
        if any(keyword in topic_lower for keyword in place_keywords):
            return "place"
        
        # Organization indicators
        org_keywords = [
            'company', 'corporation', 'university', 'school', 'institution',
            'government', 'agency', 'department', 'ministry', 'ngo',
            'foundation', 'association', 'society', 'union', 'federation',
            'bank', 'hospital', 'laboratory', 'institute', 'research center'
        ]
        if any(keyword in topic_lower for keyword in org_keywords):
            return "organization"
        
        # Event indicators
        event_keywords = [
            'war', 'battle', 'revolution', 'election', 'conference',
            'summit', 'treaty', 'agreement', 'disaster', 'olympics',
            'world cup', 'championship', 'protest', 'movement', 'celebration',
            'festival', 'ceremony', 'anniversary', 'centennial'
        ]
        if any(keyword in topic_lower for keyword in event_keywords):
            return "event"
        
        # Concept indicators (default for abstract topics)
        concept_keywords = [
            'concept', 'theory', 'philosophy', 'ethics', 'morality',
            'justice', 'freedom', 'democracy', 'equality', 'rights',
            'religion', 'faith', 'spirituality', 'meaning', 'purpose',
            'psychology', 'sociology', 'anthropology', 'linguistics',
            'economics', 'politics', 'history', 'art', 'culture'
        ]
        if any(keyword in topic_lower for keyword in concept_keywords):
            return "concept"
        
        # Default
        return "concept"

    def _generate_sub_questions(self, topic: str, topic_type: str) -> tuple:
        """
        Generate appropriate sub-questions based on topic type.
        
        Args:
            topic: The research topic
            topic_type: Detected topic type
            
        Returns:
            tuple: (sub_questions, research_query)
        """
        if topic_type == "person":
            sub_questions = [
                f"Who is {topic}?",
                f"What are {topic}'s major achievements?",
                f"Why is {topic} important?",
                f"What is {topic}'s legacy?",
            ]
            research_query = topic
            
        elif topic_type == "technology":
            sub_questions = [
                f"What is the current state of {topic}?",
                f"What are the latest developments in {topic}?",
                f"What are the key challenges in {topic}?",
                f"What is the future of {topic}?",
            ]
            research_query = f"latest developments in {topic}"
            
        elif topic_type == "concept":
            sub_questions = [
                f"What is {topic}?",
                f"What are the key principles of {topic}?",
                f"Why is {topic} important?",
                f"How does {topic} work?",
            ]
            research_query = f"{topic} explained"
            
        elif topic_type == "event":
            sub_questions = [
                f"What happened during {topic}?",
                f"When did {topic} occur?",
                f"Why is {topic} significant?",
                f"What were the consequences of {topic}?",
            ]
            research_query = f"{topic} history"
            
        elif topic_type == "place":
            sub_questions = [
                f"Where is {topic}?",
                f"What is {topic} known for?",
                f"What is the history of {topic}?",
                f"What are the key facts about {topic}?",
            ]
            research_query = f"{topic} facts"
            
        elif topic_type == "organization":
            sub_questions = [
                f"What is {topic}?",
                f"What does {topic} do?",
                f"When was {topic} founded?",
                f"Why is {topic} important?",
            ]
            research_query = f"{topic} organization"
            
        else:
            # Generic fallback
            sub_questions = [
                f"What is the current state of {topic}?",
                f"Who are the key players / sources for {topic}?",
                f"What are the main controversies or open questions in {topic}?",
                f"What changed most recently regarding {topic}?",
            ]
            research_query = topic
            
        return sub_questions, research_query

    def _summarize_text(self, text: str, max_length: int = 500) -> str:
        """
        Smart summarization by taking key sentences.
        
        Args:
            text: Text to summarize
            max_length: Maximum summary length
            
        Returns:
            str: Summarized text
        """
        if not text:
            return ""
        
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()
        
        if len(text) <= max_length:
            return text
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Find key sentences (first sentence of each paragraph)
        key_sentences = []
        current_length = 0
        
        # Always include the first sentence
        if sentences:
            first_sentence = sentences[0]
            key_sentences.append(first_sentence)
            current_length += len(first_sentence)
        
        # Add more sentences until we reach max_length
        for sentence in sentences[1:]:
            if current_length + len(sentence) + 1 <= max_length:
                key_sentences.append(sentence)
                current_length += len(sentence) + 1
            else:
                break
        
        summary = ' '.join(key_sentences)
        
        # If we still have more content, add ellipsis
        if len(summary) < len(text):
            summary += "..."
        
        return summary

    def _extract_keywords_simple(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Simple keyword extraction using regex and frequency.
        
        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List[str]: Extracted keywords
        """
        # Common stopwords
        stopwords = {
            'the', 'a', 'an', 'of', 'to', 'for', 'with', 'on', 'at', 'from',
            'by', 'in', 'as', 'is', 'was', 'were', 'are', 'and', 'or', 'but',
            'not', 'for', 'nor', 'so', 'yet', 'this', 'that', 'these', 'those',
            'it', 'he', 'she', 'they', 'we', 'you', 'i', 'me', 'us', 'them',
            'about', 'against', 'between', 'through', 'during', 'without',
            'after', 'before', 'above', 'below', 'over', 'under', 'again',
            'then', 'now', 'there', 'here', 'all', 'any', 'both', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'than', 'too',
            'very', 'way', 'use', 'also', 'well', 'get', 'one', 'two'
        }
        
        # Extract words (3+ characters, alphanumeric)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Count frequency
        word_freq = {}
        for word in words:
            if word not in stopwords:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:max_keywords]]

    def _score_domain(self, url: str) -> float:
        """
        Score domain authority based on known trusted domains.
        
        Args:
            url: URL to score
            
        Returns:
            float: Domain score (0.0 to 1.0)
        """
        trusted_domains = {
            'wikipedia.org': 1.0,
            'britannica.com': 0.95,
            'nature.com': 0.95,
            'science.org': 0.95,
            'arxiv.org': 0.9,
            'ieee.org': 0.9,
            'acm.org': 0.9,
            'plos.org': 0.9,
            'nih.gov': 0.9,
            'cambridge.org': 0.88,
            'oxford.com': 0.88,
            'springer.com': 0.88,
            'elsevier.com': 0.88,
            'edu': 0.85,
            'gov': 0.85,
            'bbc.com': 0.75,
            'reuters.com': 0.75,
            'apnews.com': 0.75,
            'forbes.com': 0.6,
            'wired.com': 0.6,
            'techcrunch.com': 0.6,
            'nytimes.com': 0.7,
            'wsj.com': 0.7,
            'theguardian.com': 0.7,
        }
        
        url_lower = url.lower()
        for domain, score in trusted_domains.items():
            if domain in url_lower:
                return score
        
        # Default based on TLD
        if url_lower.endswith('.edu'):
            return 0.7
        elif url_lower.endswith('.gov'):
            return 0.7
        elif url_lower.endswith('.org'):
            return 0.5
        elif url_lower.endswith('.com'):
            return 0.4
        else:
            return 0.3

    def _format_summary(self, summary: str, documents: List[dict]) -> dict:
        """
        Format the summary with sources in a structured way.
        
        Args:
            summary: The summary text
            documents: List of source documents
            
        Returns:
            dict: Structured summary with sources
        """
        # Extract source information
        sources = []
        for doc in documents:
            if isinstance(doc, dict):
                title = doc.get("title", "")
                url = doc.get("url", "")
                if title:
                    sources.append({
                        "title": title,
                        "url": url
                    })
        
        # Build structured output
        return {
            "summary": summary,
            "source_count": len(sources),
            "sources": sources
        }

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "plan":
            topic = params["topic"]
            
            # Detect topic type
            topic_type = self._detect_topic_type(topic)
            
            # Generate appropriate sub-questions
            sub_questions, research_query = self._generate_sub_questions(topic, topic_type)
            
            logger.info(f"Topic type detected: {topic_type}")
            logger.info(f"Generated {len(sub_questions)} sub-questions")
            
            return {
                "topic": topic,
                "topic_type": topic_type,
                "research_query": research_query,
                "sub_questions": sub_questions,
                "suggested_agents": ["browser", "rag", "memory"],
            }

        if action == "summarize":
            documents = params.get("documents", [])
            
            if not documents:
                return {
                    "summary": "No documents provided to summarize.",
                    "source_count": 0,
                    "sources": []
                }
            
            # Collect all text from documents
            all_text = ""
            for doc in documents:
                if isinstance(doc, dict):
                    text = doc.get("text", "")
                    if not text and "content" in doc:
                        text = doc["content"]
                    if not text and "body" in doc:
                        text = doc["body"]
                    all_text += text + " "
                elif isinstance(doc, str):
                    all_text += doc + " "
            
            # Generate summary
            summary = self._summarize_text(all_text, max_length=500)
            
            # Format with sources
            return self._format_summary(summary, documents)

        if action == "extract_keywords":
            text = params.get("text", "")
            if not text:
                return []
            
            keywords = self._extract_keywords_simple(text)
            return {
                "keywords": keywords,
                "count": len(keywords)
            }

        if action == "rank_sources":
            results = params.get("results", [])
            topic = params.get("topic", "")
            
            if not results:
                return {
                    "ranked_sources": [],
                    "total_sources": 0
                }
            
            # Score each source
            scored_results = []
            for i, result in enumerate(results):
                score = 0.0
                reasons = []
                
                if isinstance(result, dict):
                    title = result.get("title", "").lower()
                    snippet = result.get("snippet", "").lower()
                    url = result.get("url", "").lower()
                    
                    # 1. Domain authority score
                    domain_score = self._score_domain(url)
                    score += domain_score
                    if domain_score > 0.7:
                        reasons.append("high authority domain")
                    elif domain_score > 0.5:
                        reasons.append("moderate authority domain")
                    
                    # 2. Keyword relevance
                    if topic:
                        topic_words = set(topic.lower().split())
                        title_words = set(title.split())
                        snippet_words = set(snippet.split())
                        
                        # Title match
                        title_match = len(topic_words & title_words)
                        if title_match > 0:
                            score += 0.2 * min(title_match, 3)
                            reasons.append(f"title contains topic keywords ({title_match})")
                        
                        # Snippet match
                        snippet_match = len(topic_words & snippet_words)
                        if snippet_match > 0:
                            score += 0.1 * min(snippet_match, 5)
                            reasons.append(f"snippet contains topic keywords ({snippet_match})")
                    
                    # 3. Text length (more content is better)
                    text_length = len(result.get("text", ""))
                    if text_length > 1000:
                        score += 0.15
                        reasons.append("substantial content (>1000 chars)")
                    elif text_length > 500:
                        score += 0.08
                        reasons.append("good content length (>500 chars)")
                    
                    # 4. Freshness (URL with year in it)
                    year_match = re.search(r'(202[0-6])', url)
                    if year_match:
                        score += 0.1
                        reasons.append(f"recent content ({year_match.group(1)})")
                    
                    # 5. Search engine position bias
                    if i == 0:
                        score += 0.15
                        reasons.append("top search result")
                    elif i < 3:
                        score += 0.08
                        reasons.append("high search ranking")
                
                scored_results.append({
                    "source": result,
                    "score": score,
                    "reasons": reasons,
                    "original_rank": i
                })
            
            # Sort by score (descending)
            ranked = sorted(scored_results, key=lambda x: x["score"], reverse=True)
            
            logger.info(f"Ranked {len(ranked)} sources")
            if ranked:
                logger.debug(f"Top source: {ranked[0]['source'].get('title', '')[:50]} (score: {ranked[0]['score']:.2f})")
            
            return {
                "ranked_sources": [r["source"] for r in ranked],
                "total_sources": len(ranked),
                "scores": [r["score"] for r in ranked],
                "reasons": [r["reasons"] for r in ranked]
            }

        if action == "verify_sources":
            results = params.get("results", [])
            
            if not results:
                return {
                    "verified_sources": [],
                    "duplicates_removed": 0,
                    "total_sources": 0,
                    "verified_count": 0
                }
            
            # Remove duplicates based on URL or title
            seen_urls = {}
            seen_titles = {}
            unique_sources = []
            duplicates_removed = 0
            
            for result in results:
                # Get a unique identifier for the source
                if isinstance(result, dict):
                    # Try to use URL as unique identifier
                    url = result.get("url", "")
                    if url:
                        # Normalize URL for comparison
                        url_normalized = url.lower().strip().rstrip('/')
                        if url_normalized in seen_urls:
                            duplicates_removed += 1
                            continue
                        seen_urls[url_normalized] = True
                    
                    # Also check title similarity
                    title = result.get("title", "")
                    if title:
                        title_normalized = title.lower().strip()[:50]
                        if title_normalized in seen_titles:
                            # If URLs are different but titles are the same, keep the one with better content
                            existing = seen_titles[title_normalized]
                            existing_text = existing.get("text", "")
                            new_text = result.get("text", "")
                            if len(new_text) > len(existing_text):
                                # Replace with better version
                                unique_sources.remove(existing)
                                unique_sources.append(result)
                                seen_titles[title_normalized] = result
                            continue
                        seen_titles[title_normalized] = result
                    
                    unique_sources.append(result)
                else:
                    # Non-dict items, keep them
                    unique_sources.append(result)
            
            logger.info(f"Verified {len(unique_sources)} sources ({duplicates_removed} duplicates removed)")
            
            return {
                "verified_sources": unique_sources,
                "duplicates_removed": duplicates_removed,
                "total_sources": len(results),
                "verified_count": len(unique_sources)
            }

        # Unknown action
        raise ValueError(f"Unknown action: {action}")