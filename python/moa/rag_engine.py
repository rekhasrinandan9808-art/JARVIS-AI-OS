"""
moa/rag_engine.py
RAG (Retrieval-Augmented Generation) Engine for JARVIS
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG dependencies not installed. Install chromadb and sentence-transformers")

logger = logging.getLogger("jarvis.rag_engine")


class RAGEngine:
    """
    RAG Engine for JARVIS - Ground responses in your personal data.
    
    Use Cases:
    1. Document Q&A - Ask about your files
    2. Email Search - Find emails and summarize
    3. Knowledge Base - Store and retrieve facts
    4. Web Research - Ground answers in search results
    5. Code Repository - Ask about your code
    """
    
    def __init__(self, persist_dir: str = None):
        if not RAG_AVAILABLE:
            raise ImportError("RAG dependencies not installed")
        
        if persist_dir is None:
            persist_dir = Path(__file__).parent.parent / "data" / "rag_db"
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Embedding model
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Collections for different data types
        self.documents = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        self.emails = self.client.get_or_create_collection(
            name="emails",
            metadata={"hnsw:space": "cosine"}
        )
        self.code = self.client.get_or_create_collection(
            name="code",
            metadata={"hnsw:space": "cosine"}
        )
        self.web = self.client.get_or_create_collection(
            name="web",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info("RAG Engine initialized")
    
    def index_document(self, content: str, metadata: Dict) -> str:
        """Index a document for retrieval."""
        embedding = self.embedder.encode(content).tolist()
        doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        self.documents.add(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[content]
        )
        
        logger.info(f"Indexed document: {metadata.get('title', 'Untitled')}")
        return doc_id
    
    def search_documents(self, query: str, limit: int = 5) -> List[Dict]:
        """Search indexed documents."""
        embedding = self.embedder.encode(query).tolist()
        results = self.documents.query(
            query_embeddings=[embedding],
            n_results=limit
        )
        
        documents = []
        if results and results.get('documents'):
            for i in range(len(results['documents'][0])):
                documents.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': results['distances'][0][i] if results.get('distances') else None
                })
        return documents
    
    def index_code(self, content: str, language: str, path: str) -> str:
        """Index code for search."""
        metadata = {
            "language": language,
            "path": path,
            "type": "code"
        }
        return self.index_document(content, metadata)
    
    def search_code(self, query: str, language: str = None) -> List[Dict]:
        """Search indexed code."""
        embedding = self.embedder.encode(query).tolist()
        where = {"language": language} if language else None
        results = self.code.query(
            query_embeddings=[embedding],
            n_results=10,
            where=where
        )
        
        code_results = []
        if results and results.get('documents'):
            for i in range(len(results['documents'][0])):
                code_results.append({
                    'code': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': results['distances'][0][i] if results.get('distances') else None
                })
        return code_results
    
    def get_context_for_prompt(self, query: str, context_type: str = "documents") -> str:
        """
        Get relevant context to augment an LLM prompt.
        """
        context_parts = []
        
        # Search documents
        if context_type in ["documents", "all"]:
            docs = self.search_documents(query, limit=3)
            if docs:
                context_parts.append("Relevant documents:\n")
                for doc in docs:
                    context_parts.append(f"- {doc['content'][:500]}...")
                    if doc.get('metadata', {}).get('title'):
                        context_parts.append(f"  (Source: {doc['metadata']['title']})")
                context_parts.append("")
        
        # Search web if available
        if context_type in ["web", "all"]:
            web_results = self.search_web(query, limit=2)
            if web_results:
                context_parts.append("Relevant web results:\n")
                for result in web_results:
                    context_parts.append(f"- {result['title']}: {result['snippet']}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def search_web(self, query: str, limit: int = 3) -> List[Dict]:
        """Search web results (via Tavily integration)."""
        try:
            from agents.search.agent import SearchAgent
            agent = SearchAgent()
            result = agent._search({"query": query, "max_results": limit})
            if result.get("success"):
                return result.get("results", [])
        except Exception as e:
            logger.error(f"Web search error: {e}")
        
        return []
    
    def get_stats(self) -> Dict:
        """Get RAG statistics."""
        return {
            "documents": self.documents.count(),
            "emails": self.emails.count(),
            "code": self.code.count(),
            "web": self.web.count(),
            "total": self.documents.count() + self.emails.count() + self.code.count() + self.web.count()
        }