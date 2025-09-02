from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from app.core.config import settings
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.embedding_model = None
        self.index = None
        self.dimension = None
        self.texts = []  # In production, use a database
        self.metadata = []  # In production, use a database
    
    async def initialize(self):
        """Initialize the vector store."""
        if self.embedding_model is not None:
            return
        
        try:
            # Load embedding model
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self.dimension = self.embedding_model.get_sentence_embedding_dimension()
            
            # Initialize FAISS index
            self.index = faiss.IndexFlatIP(self.dimension)
            
            logger.info("Vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk = ' '.join(words[i:i + settings.CHUNK_SIZE])
            chunks.append(chunk)
            i += settings.CHUNK_SIZE - settings.CHUNK_OVERLAP
        
        return chunks
    
    async def add_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a document to the vector store."""
        if self.embedding_model is None:
            await self.initialize()
        
        try:
            # Chunk document
            chunks = self._chunk_text(text)
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(chunks, convert_to_tensor=True)
            embeddings = embeddings.cpu().numpy()
            
            # Add to FAISS index
            self.index.add(embeddings)
            
            # Store text and metadata
            start_idx = len(self.texts)
            for i, chunk in enumerate(chunks):
                self.texts.append(chunk)
                chunk_metadata = {
                    "chunk_index": start_idx + i,
                    "document_id": len(self.metadata),
                    "timestamp": datetime.utcnow().isoformat(),
                    **metadata if metadata else {}
                }
                self.metadata.append(chunk_metadata)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding document to vector store: {str(e)}")
            return False
    
    async def search(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks in the vector store."""
        if self.embedding_model is None:
            await self.initialize()
        
        if len(self.texts) == 0:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query, convert_to_tensor=True)
            query_embedding = query_embedding.cpu().numpy().reshape(1, -1)
            
            # Search in FAISS index
            distances, indices = self.index.search(query_embedding, k)
            
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if distance < threshold:
                    continue
                
                result = {
                    "text": self.texts[idx],
                    "score": float(distance),
                    "metadata": self.metadata[idx]
                }
                results.append(result)
            
            return sorted(results, key=lambda x: x["score"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            return []
    
    def clear(self):
        """Clear the vector store."""
        if self.index is not None:
            self.index = faiss.IndexFlatIP(self.dimension)
        self.texts = []
        self.metadata = []
    
    async def save(self, path: str):
        """Save the vector store to disk."""
        try:
            # Save FAISS index
            faiss.write_index(self.index, f"{path}/index.faiss")
            
            # Save texts and metadata
            with open(f"{path}/data.json", "w") as f:
                json.dump({
                    "texts": self.texts,
                    "metadata": self.metadata
                }, f)
            
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}")
            raise
    
    async def load(self, path: str):
        """Load the vector store from disk."""
        try:
            # Load FAISS index
            self.index = faiss.read_index(f"{path}/index.faiss")
            
            # Load texts and metadata
            with open(f"{path}/data.json", "r") as f:
                data = json.load(f)
                self.texts = data["texts"]
                self.metadata = data["metadata"]
            
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            raise

# Create global vector store instance
vector_store = VectorStore()