"""Celery tasks for repository ingestion and parsing.

AAET-87: Celery Integration
"""

import asyncio
import logging
from typing import Any

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from workers.celery_app import celery_app
from services.ingestion.parser_service import ParserService, TenantValidationError, RepositoryParseError
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
    name="workers.tasks.ingestion.parse_and_index_repository",
    max_retries=3,
    default_retry_delay=60,  # 1 minute base delay
    autoretry_for=(StorageError, ConnectionError),
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,  # Add randomness to prevent thundering herd
)
def parse_and_index_repository(
    self: Task,
    tenant_id: str,
    repo_id: str,
    repo_path: str,
    connection_string: str,
) -> dict[str, Any]:
    """Parse and index a repository in the background.
    
    This task:
    1. Connects to PostgreSQL storage
    2. Creates ParserService
    3. Parses repository with tenant context
    4. Updates task progress
    5. Returns metrics
    
    Args:
        tenant_id: Tenant identifier for multi-tenant isolation
        repo_id: Repository identifier
        repo_path: Path to repository on disk
        connection_string: PostgreSQL connection string
    
    Returns:
        dict with keys:
            - success: bool
            - nodes_created: int
            - edges_created: int
            - parse_time_seconds: float
            - error: str (if failed)
    
    Raises:
        TenantValidationError: If tenant_id or repo_id invalid
        RepositoryParseError: If parsing fails (after retries)
        StorageError: If database operations fail (will auto-retry)
    
    Example:
        ```python
        from workers.tasks import parse_and_index_repository
        
        # Async execution
        task = parse_and_index_repository.delay(
            tenant_id="tenant-123",
            repo_id="repo-456",
            repo_path="/path/to/repo",
            connection_string="postgresql://..."
        )
        
        # Check status
        print(task.state)  # PENDING, STARTED, SUCCESS, FAILURE
        
        # Get result (blocks until complete)
        result = task.get(timeout=3600)
        print(f"Created {result['nodes_created']} nodes")
        ```
    """
    logger.info(
        "Starting repository parse task",
        extra={
            "task_id": self.request.id,
            "tenant_id": tenant_id,
            "repo_id": repo_id,
            "repo_path": repo_path,
        }
    )
    
    # Update task state to STARTED
    self.update_state(
        state="STARTED",
        meta={
            "status": "Initializing parser",
            "progress": 0,
            "tenant_id": tenant_id,
            "repo_id": repo_id,
        }
    )
    
    store = None
    
    try:
        # Initialize storage (async operation wrapped in sync task)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Update progress: Connecting to database
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "Connecting to database",
                    "progress": 10,
                    "tenant_id": tenant_id,
                    "repo_id": repo_id,
                }
            )
            
            # Connect to storage
            store = PostgresGraphStore(connection_string)
            loop.run_until_complete(store.connect())
            
            logger.info(
                "Connected to storage",
                extra={
                    "task_id": self.request.id,
                    "tenant_id": tenant_id,
                }
            )
            
            # Update progress: Creating parser service
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "Creating parser service",
                    "progress": 20,
                    "tenant_id": tenant_id,
                    "repo_id": repo_id,
                }
            )
            
            # Create parser service
            service = ParserService(store)
            
            # Update progress: Parsing repository
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "Parsing repository",
                    "progress": 30,
                    "tenant_id": tenant_id,
                    "repo_id": repo_id,
                }
            )
            
            # Parse repository
            result = loop.run_until_complete(
                service.parse_repository(
                    tenant_id=tenant_id,
                    repo_id=repo_id,
                    repo_path=repo_path,
                )
            )
            
            # Update progress: Complete
            self.update_state(
                state="PROGRESS",
                meta={
                    "status": "Parse complete",
                    "progress": 100,
                    "tenant_id": tenant_id,
                    "repo_id": repo_id,
                    "nodes_created": result.nodes_created,
                    "edges_created": result.edges_created,
                }
            )
            
            logger.info(
                "Repository parse task complete",
                extra={
                    "task_id": self.request.id,
                    "tenant_id": tenant_id,
                    "repo_id": repo_id,
                    "nodes_created": result.nodes_created,
                    "edges_created": result.edges_created,
                    "parse_time_seconds": result.parse_time_seconds,
                }
            )
            
            return result.to_dict()
            
        finally:
            # Clean up storage connection
            if store:
                loop.run_until_complete(store.close())
            loop.close()
    
    except TenantValidationError as e:
        # Validation errors should not be retried
        logger.error(
            f"Tenant validation failed: {e}",
            extra={
                "task_id": self.request.id,
                "tenant_id": tenant_id,
                "repo_id": repo_id,
            }
        )
        return {
            "success": False,
            "error": f"Tenant validation failed: {e}",
            "nodes_created": 0,
            "edges_created": 0,
            "parse_time_seconds": 0,
        }
    
    except RepositoryParseError as e:
        # Parse errors should not be retried (bad input)
        logger.error(
            f"Repository parse failed: {e}",
            extra={
                "task_id": self.request.id,
                "tenant_id": tenant_id,
                "repo_id": repo_id,
            }
        )
        return {
            "success": False,
            "error": f"Repository parse failed: {e}",
            "nodes_created": 0,
            "edges_created": 0,
            "parse_time_seconds": 0,
        }
    
    except SoftTimeLimitExceeded:
        # Task took too long
        logger.error(
            "Task exceeded time limit",
            extra={
                "task_id": self.request.id,
                "tenant_id": tenant_id,
                "repo_id": repo_id,
            }
        )
        return {
            "success": False,
            "error": "Task exceeded time limit",
            "nodes_created": 0,
            "edges_created": 0,
            "parse_time_seconds": 0,
        }
    
    except (StorageError, ConnectionError) as e:
        # These errors will be auto-retried by Celery
        logger.warning(
            f"Retryable error occurred: {e}",
            extra={
                "task_id": self.request.id,
                "tenant_id": tenant_id,
                "repo_id": repo_id,
                "retry_count": self.request.retries,
            }
        )
        # Celery will automatically retry due to autoretry_for
        raise
    
    except Exception as e:
        # Unexpected errors - log and return failure
        logger.error(
            f"Unexpected error in parse task: {e}",
            extra={
                "task_id": self.request.id,
                "tenant_id": tenant_id,
                "repo_id": repo_id,
            },
            exc_info=True
        )
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "nodes_created": 0,
            "edges_created": 0,
            "parse_time_seconds": 0,
        }
