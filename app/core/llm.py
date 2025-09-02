from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from vllm import AsyncLLMEngine, AsyncEngineArgs
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import asyncio
import torch
from typing import List, Dict, Any, Optional
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class LLMManager:
    def __init__(self):
        self.engine = None
        self.tokenizer = None
        self.embedding_model = None
        self.vector_index = None
        self._setup_complete = False
    
    async def setup(self):
        """Initialize LLM components."""
        if self._setup_complete:
            return
        
        try:
            # Initialize vLLM engine
            engine_args = AsyncEngineArgs(
                model=settings.DEFAULT_MODEL,
                download_dir="./models",
                quantization="awq" if torch.cuda.is_available() else None,
                max_model_len=settings.MAX_CONTEXT_WINDOW,
                gpu_memory_utilization=0.9
            )
            
            self.engine = AsyncLLMEngine.from_engine_args(engine_args)
            
            # Initialize tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(settings.DEFAULT_MODEL)
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            
            # Initialize FAISS index
            self.vector_index = faiss.IndexFlatIP(self.embedding_model.get_sentence_embedding_dimension())
            
            self._setup_complete = True
            logger.info("LLM infrastructure initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM infrastructure: {str(e)}")
            raise
    
    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate response using vLLM."""
        if not self._setup_complete:
            await self.setup()
        
        try:
            # Prepare full prompt with context
            full_prompt = f"{context}\n\n{prompt}" if context else prompt
            
            # Set generation parameters
            sampling_params = {
                "temperature": temperature or settings.TEMPERATURE,
                "top_p": settings.TOP_P,
                "max_tokens": max_tokens or settings.MAX_TOKENS,
            }
            
            # Generate response
            responses = await self.engine.generate(full_prompt, sampling_params)
            
            if responses and responses[0].outputs:
                return responses[0].outputs[0].text
            
            return "I apologize, but I couldn't generate a response. Please try again."
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "I encountered an error while processing your request. Please try again."
    
    async def add_to_vector_store(
        self,
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Add texts to vector store with optional metadata."""
        if not self._setup_complete:
            await self.setup()
        
        try:
            # Generate embeddings
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=True)
            embeddings = embeddings.cpu().numpy()
            
            # Add to FAISS index
            self.vector_index.add(embeddings)
            
            # Store metadata if provided
            if metadata:
                # In a real implementation, store metadata in a database
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding to vector store: {str(e)}")
            return False
    
    async def search_similar(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar texts in vector store."""
        if not self._setup_complete:
            await self.setup()
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query, convert_to_tensor=True)
            query_embedding = query_embedding.cpu().numpy().reshape(1, -1)
            
            # Search in FAISS index
            distances, indices = self.vector_index.search(query_embedding, k)
            
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                result = {
                    "index": idx,
                    "score": float(distance),
                    # In a real implementation, fetch text and metadata from database
                    "text": f"Document {idx}",
                    "metadata": {}
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            return []

# Create global LLM manager instance
llm_manager = LLMManager()