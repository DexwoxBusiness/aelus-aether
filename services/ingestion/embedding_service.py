"""Embedding service for generating vector embeddings using Voyage AI.

AAET-87: Full Voyage AI Integration
"""

import asyncio
import logging
import os
from typing import Any

try:
    import voyageai
except ImportError:
    voyageai = None

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """Base exception for embedding service errors.
    
    Args:
        message: Error message
        details: Optional additional error details
    """
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class VoyageAPIError(EmbeddingServiceError):
    """Raised when Voyage API returns an error.
    
    Args:
        message: Error message
        status_code: HTTP status code from Voyage API
        details: Optional additional error details
    """
    
    def __init__(self, message: str, status_code: int | None = None, details: dict[str, Any] | None = None):
        super().__init__(message, details)
        self.status_code = status_code


class VoyageRateLimitError(VoyageAPIError):
    """Raised when Voyage API rate limit is exceeded (429).
    
    Args:
        message: Error message
        retry_after: Seconds to wait before retrying (from Retry-After header)
        details: Optional additional error details
    """
    
    def __init__(self, message: str, retry_after: int | None = None, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=429, details=details)
        self.retry_after = retry_after


class EmbeddingService:
    """Service for generating embeddings from code chunks using Voyage AI.
    
    Uses voyage-code-3 model (1024-dimensional embeddings) optimized for code.
    Handles batching (max 96 chunks per request), rate limiting, and retries.
    
    Example:
        ```python
        service = EmbeddingService()
        embeddings = await service.embed_batch(
            chunks=[
                {"text": "def hello(): pass", "metadata": {"type": "function"}},
                {"text": "class Foo: pass", "metadata": {"type": "class"}}
            ]
        )
        # Returns: [{"chunk_id": "0", "embedding": [0.1, ...], "metadata": {...}}, ...]
        ```
    """
    
    # Voyage API limits (configurable via app.config.settings)
    MAX_RETRIES = 3  # Maximum retries for failed requests
    
    @property
    def MAX_BATCH_SIZE(self) -> int:
        """Maximum chunks per API request (from config)."""
        return settings.voyage_max_batch_size
    
    @property
    def RATE_LIMIT_DELAY(self) -> float:
        """Seconds between batches to avoid 429 (from config)."""
        return settings.voyage_rate_limit_delay
    
    def __init__(self, api_key: str | None = None):
        """Initialize embedding service.
        
        Args:
            api_key: Voyage AI API key (optional, will use VOYAGE_API_KEY env var if not provided)
        
        Raises:
            EmbeddingServiceError: If voyageai package is not installed or API key is missing
        """
        if voyageai is None:
            raise EmbeddingServiceError(
                "voyageai package is required. Install it with: pip install voyageai>=0.2.0"
            )
        
        self.api_key = api_key or settings.voyage_api_key or os.getenv("VOYAGE_API_KEY")
        if not self.api_key:
            raise EmbeddingServiceError(
                "Voyage API key is required. Set VOYAGE_API_KEY environment variable or pass api_key parameter."
            )
        
        self.client = voyageai.Client(api_key=self.api_key)
        logger.info(
            f"EmbeddingService initialized with Voyage AI ({settings.voyage_model_name}, {settings.voyage_embedding_dimension}-d)",
            extra={
                "model": settings.voyage_model_name,
                "dimension": settings.voyage_embedding_dimension,
                "max_batch_size": self.MAX_BATCH_SIZE,
                "rate_limit_delay": self.RATE_LIMIT_DELAY
            }
        )
    
    async def generate_embeddings(
        self,
        chunks: list[str],
        model: str | None = None
    ) -> list[list[float]]:
        """Generate embeddings for code chunks.
        
        Args:
            chunks: List of code chunks to embed
            model: Embedding model to use (default: voyage-code-3)
        
        Returns:
            List of embedding vectors (each is list of 1024 floats)
        
        Raises:
            VoyageRateLimitError: If rate limit is exceeded
            VoyageAPIError: If API returns an error
            EmbeddingServiceError: For other errors
        """
        if not chunks:
            return []
        
        # Use configured model if not specified
        model = model or settings.voyage_model_name
        
        logger.info(
            f"Generating embeddings for {len(chunks)} chunks using {model}",
            extra={"chunk_count": len(chunks), "model": model}
        )
        
        try:
            # Voyage AI SDK is synchronous, so we run it in a thread pool executor
            # to avoid blocking the async event loop. This is the recommended pattern
            # for integrating sync libraries in async code (per AAET-85 async architecture).
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.embed(
                    texts=chunks,
                    model=model,
                    input_type="document"  # Use 'document' for code chunks
                )
            )
            
            embeddings = result.embeddings
            logger.info(
                f"Successfully generated {len(embeddings)} embeddings",
                extra={"chunk_count": len(embeddings), "dimension": len(embeddings[0]) if embeddings else 0}
            )
            
            return embeddings
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limit errors
            if "429" in error_msg or "rate limit" in error_msg:
                raise VoyageRateLimitError(f"Voyage API rate limit exceeded: {e}") from e
            
            # Check for API errors
            if "500" in error_msg or "503" in error_msg or "api error" in error_msg:
                raise VoyageAPIError(f"Voyage API error: {e}") from e
            
            # Other errors
            raise EmbeddingServiceError(f"Failed to generate embeddings: {e}") from e
    
    async def embed_batch(
        self,
        chunks: list[dict[str, Any]],
        model: str | None = None
    ) -> list[dict[str, Any]]:
        """Generate embeddings for a batch of chunks with batching and rate limiting.
        
        Handles Voyage API limits:
        - Max 96 chunks per request
        - Rate limiting with delays between batches
        - Retries with exponential backoff
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata' keys
            model: Embedding model to use (default: voyage-code-3)
        
        Returns:
            List of embedding dictionaries with 'chunk_id', 'embedding', 'metadata' keys
        
        Raises:
            EmbeddingServiceError: If all retries fail
        """
        if not chunks:
            return []
        
        # Use configured model if not specified
        model = model or settings.voyage_model_name
        
        logger.info(
            f"Starting batch embedding generation for {len(chunks)} chunks",
            extra={"chunk_count": len(chunks), "model": model, "batch_size": self.MAX_BATCH_SIZE}
        )
        
        all_embeddings = []
        failed_chunks = []
        
        # Process in batches of MAX_BATCH_SIZE
        for batch_idx in range(0, len(chunks), self.MAX_BATCH_SIZE):
            batch = chunks[batch_idx:batch_idx + self.MAX_BATCH_SIZE]
            batch_num = batch_idx // self.MAX_BATCH_SIZE + 1
            total_batches = (len(chunks) + self.MAX_BATCH_SIZE - 1) // self.MAX_BATCH_SIZE
            
            logger.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)",
                extra={"batch_num": batch_num, "total_batches": total_batches, "batch_size": len(batch)}
            )
            
            # Extract texts from batch
            texts = [chunk.get("text", "") for chunk in batch]
            
            # Retry logic for this batch
            for retry in range(self.MAX_RETRIES):
                try:
                    # Generate embeddings for this batch
                    embeddings = await self.generate_embeddings(texts, model)
                    
                    # Combine with metadata
                    for i, (chunk, embedding) in enumerate(zip(batch, embeddings)):
                        all_embeddings.append({
                            "chunk_id": chunk.get("chunk_id", f"chunk_{batch_idx + i}"),
                            "embedding": embedding,
                            "metadata": chunk.get("metadata", {})
                        })
                    
                    logger.info(
                        f"Batch {batch_num}/{total_batches} completed successfully",
                        extra={"batch_num": batch_num, "embeddings_count": len(embeddings)}
                    )
                    
                    break  # Success, exit retry loop
                    
                except VoyageRateLimitError as e:
                    # Rate limit - wait longer and retry
                    wait_time = self.RATE_LIMIT_DELAY * (2 ** retry)
                    logger.warning(
                        f"Rate limit hit on batch {batch_num}, waiting {wait_time}s before retry {retry + 1}/{self.MAX_RETRIES}",
                        extra={"batch_num": batch_num, "retry": retry + 1, "wait_time": wait_time}
                    )
                    
                    if retry < self.MAX_RETRIES - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        # Max retries reached, mark chunks as failed
                        failed_chunks.extend(batch)
                        logger.error(
                            f"Batch {batch_num} failed after {self.MAX_RETRIES} retries",
                            extra={"batch_num": batch_num, "error": str(e)}
                        )
                
                except (VoyageAPIError, EmbeddingServiceError) as e:
                    # API error - retry with backoff
                    wait_time = 2 ** retry
                    logger.warning(
                        f"API error on batch {batch_num}, waiting {wait_time}s before retry {retry + 1}/{self.MAX_RETRIES}",
                        extra={"batch_num": batch_num, "retry": retry + 1, "wait_time": wait_time, "error": str(e)}
                    )
                    
                    if retry < self.MAX_RETRIES - 1:
                        await asyncio.sleep(wait_time)
                    else:
                        # Max retries reached, mark chunks as failed
                        failed_chunks.extend(batch)
                        logger.error(
                            f"Batch {batch_num} failed after {self.MAX_RETRIES} retries",
                            extra={"batch_num": batch_num, "error": str(e)}
                        )
            
            # Rate limiting between batches (if not last batch)
            if batch_idx + self.MAX_BATCH_SIZE < len(chunks):
                logger.debug(
                    f"Waiting {self.RATE_LIMIT_DELAY}s before next batch",
                    extra={"delay": self.RATE_LIMIT_DELAY}
                )
                await asyncio.sleep(self.RATE_LIMIT_DELAY)
        
        # Log summary
        success_count = len(all_embeddings)
        failed_count = len(failed_chunks)
        
        logger.info(
            f"Batch embedding generation complete: {success_count} successful, {failed_count} failed",
            extra={
                "total_chunks": len(chunks),
                "successful": success_count,
                "failed": failed_count,
                "success_rate": f"{success_count / len(chunks) * 100:.1f}%" if chunks else "0%"
            }
        )
        
        if failed_count > 0:
            logger.warning(
                f"{failed_count} chunks failed to generate embeddings after retries",
                extra={"failed_count": failed_count}
            )
        
        return all_embeddings
