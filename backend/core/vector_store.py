import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
import chromadb
from chromadb.config import Settings
import hashlib

from ..core.config import settings

logger = logging.getLogger(__name__)

class SemanticCache:
    """Vector-based semantic caching using ChromaDB"""

    def __init__(self):
        self.client = None
        self.collection = None
        self.initialized = False

    async def initialize(self):
        """Initialize ChromaDB client and collection"""
        if self.initialized:
            return

        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=settings.chroma_db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Get or create collection
            collection_name = "research_cache"
            try:
                self.collection = self.client.get_collection(collection_name)
            except ValueError:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "Semantic cache for research results"}
                )

            self.initialized = True
            logger.info("Semantic cache initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize semantic cache: {e}")
            raise

    async def store(self, query: str, result: Dict):
        """Store research result in semantic cache"""
        if not self.initialized:
            await self.initialize()

        try:
            # Generate document ID from query
            doc_id = hashlib.md5(query.encode()).hexdigest()

            # Prepare document content for embedding
            content = self._prepare_content(query, result)

            # Store in ChromaDB
            self.collection.add(
                documents=[content],
                metadatas=[{
                    "query": query,
                    "timestamp": result.get("completed_at", ""),
                    "result_type": "research_result"
                }],
                ids=[doc_id]
            )

            logger.debug(f"Stored result for query: {query[:50]}...")

        except Exception as e:
            logger.error(f"Failed to store in semantic cache: {e}")

    async def search_similar(self, query: str, n_results: int = 5) -> Optional[Dict]:
        """Search for similar cached results"""
        if not self.initialized:
            await self.initialize()

        try:
            # Search for similar documents
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )

            if not results["documents"] or not results["documents"][0]:
                return None

            # Find best match with reasonable similarity
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            # Use distance threshold (lower is more similar)
            min_distance = min(distances) if distances else 1.0
            if min_distance > settings.semantic_similarity_threshold:
                return None

            # Get the best match
            best_idx = distances.index(min_distance)
            best_metadata = metadatas[best_idx]

            # Reconstruct result from metadata
            # Note: In a real implementation, you'd store the full result
            # For now, we'll return a placeholder
            return self._create_cached_result(query, best_metadata)

        except Exception as e:
            logger.error(f"Failed to search semantic cache: {e}")
            return None

    async def clear_cache(self):
        """Clear all cached results"""
        if not self.initialized:
            await self.initialize()

        try:
            # Reset the collection
            collection_name = "research_cache"
            self.client.delete_collection(collection_name)
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Semantic cache for research results"}
            )
            logger.info("Semantic cache cleared")

        except Exception as e:
            logger.error(f"Failed to clear semantic cache: {e}")

    async def get_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.initialized:
            await self.initialize()

        try:
            count = self.collection.count()
            return {
                "total_entries": count,
                "collection_name": "research_cache"
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"total_entries": 0, "error": str(e)}

    def _prepare_content(self, query: str, result: Dict) -> str:
        """Prepare content for embedding from query and result"""
        summary = result.get("summary", {}).get("summary", "")
        sources = result.get("search_results", [])

        # Create a comprehensive text representation
        content_parts = [
            f"Query: {query}",
            f"Summary: {summary}"
        ]

        # Add source titles and descriptions
        for source in sources[:5]:  # Limit to top 5 sources
            if isinstance(source, dict):
                title = source.get("title", "")
                description = source.get("description", "")
                if title:
                    content_parts.append(f"Source: {title}")
                if description:
                    content_parts.append(f"Description: {description}")

        return " | ".join(content_parts)

    def _create_cached_result(self, query: str, metadata: Dict) -> Dict:
        """Create a cached result from metadata"""
        # This is a simplified reconstruction
        # In production, you'd store the full result in the vector DB
        return {
            "job_id": f"cached_{hashlib.md5(query.encode()).hexdigest()[:8]}",
            "query": query,
            "search_engines_used": ["cached"],
            "search_results": [],
            "extracted_count": 0,
            "summary": {
                "summary": "Cached result - full details not available",
                "sections": {"Note": "This is a cached result"},
                "sources": [],
                "generated_at": metadata.get("timestamp", ""),
                "word_count": 0,
                "model_used": "cached",
                "provider": "cache",
                "cost": 0.0
            },
            "completed_at": metadata.get("timestamp", ""),
            "from_cache": True
        }