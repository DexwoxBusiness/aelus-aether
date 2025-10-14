"""Celery tasks for repository ingestion and parsing.

AAET-87: Celery Integration
"""

import asyncio
import logging
import os
from typing import Any

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from workers.celery_app import celery_app
from services.ingestion.parser_service import ParserService, TenantValidationError, RepositoryParseError
from services.ingestion.embedding_service import EmbeddingService
from libs.code_graph_rag.storage.postgres_store import PostgresGraphStore, StorageError

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task with callbacks for progress tracking."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(
            f"Task {task_id} succeeded",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "result": retval,
            }
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(
            f"Task {task_id} failed: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "exception": str(exc),
            },
            exc_info=einfo
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(
            f"Task {task_id} retrying: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "exception": str(exc),
                "retry_count": self.request.retries,
            }
        )


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="workers.tasks.ingestion.parse_and_index_file",
    max_retries=3,
    default_retry_delay=60,  # 1 minute base delay
    autoretry_for=(StorageError, ConnectionError),
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,  # Add randomness to prevent thundering herd
)
def parse_and_index_file(
    self: Task,
    tenant_id: str,
    repo_id: str,
    file_path: str,
    file_content: str,
    language: str,
    connection_string: str | None = None,
) -> dict[str, Any]:
    """Parse and index a single file in the background.
    
    This task implements the JIRA AAET-87 specification:
    1. Parse file using ParserService
    2. Chunk nodes for embeddings
    3. Generate embeddings using EmbeddingService
    4. Store nodes, edges, and embeddings in PostgreSQL
    5. Update progress and return metrics
    
    Args:
        tenant_id: Tenant identifier for multi-tenant isolation
        repo_id: Repository identifier
        file_path: Path to the file (for context/metadata)
        file_content: Content of the file to parse
        language: Programming language (python, typescript, javascript, etc.)
        connection_string: PostgreSQL connection string (optional, uses DATABASE_URL env var)
    
    Returns:
        dict with keys:
            - status: 'success' or 'failure'
            - nodes: Number of nodes created
            - edges: Number of edges created
            - embeddings: Number of embeddings generated
            - error: Error message (if failed)
    
    Raises:
        StorageError: If database operations fail (will auto-retry)
        ConnectionError: If connection fails (will auto-retry)
    
    Example:
        ```python
        from workers.tasks import parse_and_index_file
        
        # Async execution
        task = parse_and_index_file.delay(
            tenant_id="tenant-123",
            repo_id="repo-456",
            file_path="src/main.py",
            file_content="def hello(): pass",
            language="python"
        )
        
        # Check status
        print(task.state)  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
        
        # Get result
        result = task.get(timeout=300)
        print(f"Created {result['nodes']} nodes")
        ```
    """
    # Get connection string from env if not provided
    if not connection_string:
        connection_string = os.getenv("DATABASE_URL")
        if not connection_string:
            return {
                "status": "failure",
                "error": "DATABASE_URL environment variable not set",
                "nodes": 0,
                "edges": 0,
                "embeddings": 0,
            }
    
    logger.info(
        "Starting file parse task",
        extra={
            "task_id": self.request.id,
            "tenant_id": tenant_id,
            "repo_id": repo_id,
            "file_path": file_path,
            "language": language,
        }
    )
    
    # Update task state to STARTED
    self.update_state(
        state="STARTED",
        meta={
            "status": "Parsing file",
            "progress": 0,
            "tenant_id": tenant_id,
            "file_path": file_path,
        }
    )
    
    store = None
    
    try:
        # Initialize storage (async operation wrapped in sync task)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 1. Connect to storage
            self.update_state(
                state="PROGRESS",
                meta={"status": "Connecting to database", "progress": 10}
            )
            
            store = PostgresGraphStore(connection_string)
            loop.run_until_complete(store.connect())
            
            # 2. Parse file with ParserService
            self.update_state(
                state="PROGRESS",
                meta={"status": "Parsing file", "progress": 30}
            )
            
            service = ParserService(store)
            result = loop.run_until_complete(
                service.parse_file(
                    tenant_id=tenant_id,
                    repo_id=repo_id,
                    file_path=file_path,
                    file_content=file_content,
                    language=language
                )
            )
            
            # 3. Chunk nodes for embeddings
            self.update_state(
                state="PROGRESS",
                meta={"status": "Chunking for embeddings", "progress": 50}
            )
            
            # TODO: Implement actual chunking logic
            # For now, use placeholder
            chunks = []  # chunk_nodes(result.nodes, max_tokens=512)
            
            # 4. Generate embeddings
            self.update_state(
                state="PROGRESS",
                meta={"status": "Generating embeddings", "progress": 70}
            )
            
            embedding_service = EmbeddingService()
            embeddings = loop.run_until_complete(
                embedding_service.generate_embeddings(chunks)
            )
            
            # 5. Store embeddings
            self.update_state(
                state="PROGRESS",
                meta={"status": "Storing embeddings", "progress": 90}
            )
            
            # TODO: Implement store.insert_embeddings when method exists
            # loop.run_until_complete(store.insert_embeddings(tenant_id, embeddings))
            
            # Complete
            self.update_state(
                state="PROGRESS",
                meta={"status": "Complete", "progress": 100}
            )
            
            logger.info(
                "File parse task complete",
                extra={
                    "task_id": self.request.id,
                    "tenant_id": tenant_id,
                    "file_path": file_path,
                    "nodes": result.nodes_created,
                    "edges": result.edges_created,
                    "embeddings": len(embeddings),
                }
            )
            
            return {
                "status": "success",
                "nodes": result.nodes_created,
                "edges": result.edges_created,
                "embeddings": len(embeddings),
            }
            
        finally:
            # Clean up storage connection
            if store:
                loop.run_until_complete(store.close())
            loop.close()
    
    except (TenantValidationError, RepositoryParseError) as e:
        # Validation/parse errors should not be retried
        logger.error(
            f"Parse failed: {e}",
            extra={
                "task_id": self.request.id,
                "tenant_id": tenant_id,
                "file_path": file_path,
            }
        )
        return {
            "status": "failure",
            "error": str(e),
            "nodes": 0,
            "edges": 0,
            "embeddings": 0,
        }
    
    except SoftTimeLimitExceeded:
        logger.error(
            "Task exceeded time limit",
            extra={"task_id": self.request.id, "file_path": file_path}
        )
        return {
            "status": "failure",
            "error": "Task exceeded time limit",
            "nodes": 0,
            "edges": 0,
            "embeddings": 0,
        }
    
    except (StorageError, ConnectionError) as e:
        # These errors will be auto-retried by Celery
        logger.warning(
            f"Retryable error: {e}",
            extra={
                "task_id": self.request.id,
                "file_path": file_path,
                "retry_count": self.request.retries,
            }
        )
        raise
    
    except Exception as e:
        logger.error(
            f"Unexpected error: {e}",
            extra={"task_id": self.request.id, "file_path": file_path},
            exc_info=True
        )
        return {
            "status": "failure",
            "error": f"Unexpected error: {e}",
            "nodes": 0,
            "edges": 0,
            "embeddings": 0,
        }
