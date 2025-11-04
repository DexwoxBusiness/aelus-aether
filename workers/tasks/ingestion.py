"""Celery tasks for repository ingestion and parsing.

AAET-87: Celery Integration
"""

import logging
import os
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Concatenate, Protocol

from typing_extensions import ParamSpec

if TYPE_CHECKING:

    class CeleryTaskProto(Protocol):
        name: str
        request: Any

        def update_state(self, state: str, meta: dict[str, Any] | None = ...) -> None: ...

        def on_success(
            self, retval: object, task_id: str, args: tuple[Any, ...], kwargs: dict[str, Any]
        ) -> None: ...

        def on_failure(
            self,
            exc: BaseException,
            task_id: str,
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
            einfo: Any,
        ) -> None: ...

        def on_retry(
            self,
            exc: BaseException,
            task_id: str,
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
            einfo: Any,
        ) -> None: ...

else:
    from celery import Task as CeleryTaskProto

from celery.exceptions import SoftTimeLimitExceeded

from app.config import settings
from app.core.metrics import embedding_tokens_total, storage_bytes_total, vector_count_total
from app.core.redis import redis_manager
from app.utils.quota import quota_service
from libs.code_graph_rag.storage.interface import StorageError
from libs.code_graph_rag.storage.postgres_store import PostgresGraphStore
from services.ingestion.embedding_service import (
    EmbeddingService,
    VoyageAPIError,
    VoyageRateLimitError,
)
from services.ingestion.parser_service import (
    ParserService,
    RepositoryParseError,
    TenantValidationError,
)
from workers.celery_app import celery_app

# Typed Celery task decorator alias so mypy knows decorated async function types
P = ParamSpec("P")


def typed_task(
    *dargs: Any, **dkwargs: Any
) -> Callable[
    [Callable[Concatenate[CeleryTaskProto, P], Awaitable[Any]]],
    Callable[Concatenate[CeleryTaskProto, P], Awaitable[Any]],
]:
    return celery_app.task(*dargs, **dkwargs)  # type: ignore[no-any-return]


logger = logging.getLogger(__name__)


def chunk_nodes(nodes: list[dict[str, Any]], max_tokens: int = 512) -> list[dict[str, Any]]:
    """Chunk nodes for embedding generation.

    Converts parsed nodes into text chunks suitable for embedding.
    Each chunk contains the node's code/documentation with metadata.

    Args:
        nodes: List of parsed nodes from ParserService
        max_tokens: Maximum tokens per chunk (approximate)

    Returns:
        List of chunk dictionaries with keys:
            - chunk_id: Unique identifier
            - text: Text content to embed
            - metadata: Node metadata (type, name, file_path, etc.)
    """
    chunks = []

    for i, node in enumerate(nodes):
        # Extract text content from node
        text_parts = []

        # Add node name/signature
        if "name" in node:
            text_parts.append(f"Name: {node['name']}")

        if "signature" in node:
            text_parts.append(f"Signature: {node['signature']}")

        # Add docstring if available
        if "docstring" in node and node["docstring"]:
            text_parts.append(f"Documentation: {node['docstring']}")

        # Add code content if available
        if "code" in node and node["code"]:
            # Truncate code to approximate max_tokens (rough estimate: 1 token ≈ 4 chars)
            max_chars = max_tokens * 4
            code = node["code"]
            if len(code) > max_chars:
                code = code[:max_chars] + "..."
            text_parts.append(f"Code:\n{code}")

        # Combine into single text
        text = "\n\n".join(text_parts)

        if not text.strip():
            continue  # Skip empty nodes

        # Create chunk
        chunk = {
            "chunk_id": f"{node.get('qualified_name', f'node_{i}')}",
            "text": text,
            "metadata": {
                "node_type": node.get("type", "unknown"),
                "name": node.get("name", ""),
                "qualified_name": node.get("qualified_name", ""),
                "file_path": node.get("file_path", ""),
                "line_number": node.get("line_number", 0),
            },
        }
        chunks.append(chunk)

    return chunks


class CallbackTask(CeleryTaskProto):
    """Base task with callbacks for progress tracking."""

    def on_success(
        self, retval: object, task_id: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> None:
        """Called when task succeeds."""
        logger.info(
            f"Task {task_id} succeeded",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "result": retval,
            },
        )

    def on_failure(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Called when task fails."""
        logger.error(
            f"Task {task_id} failed: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "exception": str(exc),
            },
            exc_info=einfo,
        )

    def on_retry(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Called when task is retried."""
        logger.warning(
            f"Task {task_id} retrying: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "exception": str(exc),
                "retry_count": self.request.retries,
            },
        )


@typed_task(
    bind=True,
    base=CallbackTask,
    max_retries=3,
    autoretry_for=(StorageError, ConnectionError, VoyageAPIError, VoyageRateLimitError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
async def parse_and_index_file(
    self: CeleryTaskProto,
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
        },
    )

    # Update task state to STARTED
    self.update_state(
        state="STARTED",
        meta={
            "status": "Parsing file",
            "progress": 0,
            "tenant_id": tenant_id,
            "file_path": file_path,
        },
    )

    store = None
    redis_available = False

    try:
        # 1. Parse file with ParserService (10%)
        self.update_state(state="PROGRESS", meta={"status": "Parsing file", "progress": 10})

        store = PostgresGraphStore(connection_string)
        await store.connect()

        service = ParserService(store)
        result = await service.parse_file(
            tenant_id=tenant_id,
            repo_id=repo_id,
            file_path=file_path,
            file_content=file_content,
            language=language,
        )

        # 2. Prepare chunks from parsed nodes (30%)
        self.update_state(state="PROGRESS", meta={"status": "Preparing chunks", "progress": 30})

        # Extract nodes from result and chunk them
        nodes = result.nodes if hasattr(result, "nodes") else []
        chunks = chunk_nodes(nodes, max_tokens=512)

        # Quota enforcement: Check BEFORE expensive embedding generation (AAET-25)
        # Initialize Redis connections if not already initialized
        if settings.environment != "test":
            try:
                await redis_manager.init_connections()
                redis_available = True
            except Exception as e:
                logger.warning(
                    f"Redis unavailable for tenant {tenant_id}, quota enforcement disabled: {e}",
                    extra={"tenant_id": tenant_id},
                )

        # Fetch quota limits from Redis cache, fallback to DB, then cache
        limits = await quota_service.get_limits(tenant_id) if redis_available else {}
        if not limits:
            try:
                # Use proper database session and Tenant model
                from sqlalchemy import select

                from app.core.database import get_db
                from app.models.tenant import Tenant

                async for db in get_db():
                    db_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
                    tenant_obj = db_result.scalar_one_or_none()
                    if tenant_obj and tenant_obj.quotas:
                        limits = dict(tenant_obj.quotas)
                        await quota_service.set_limits(tenant_id, limits, ttl_seconds=300)
                    else:
                        limits = {}
                    break  # Exit after first iteration
            except Exception as e:
                logger.warning(
                    f"Failed to fetch tenant quotas from DB: {e}",
                    extra={"tenant_id": tenant_id},
                )
                limits = {}

        # Estimate prospective usage BEFORE expensive embedding generation
        vectors_to_add = len(chunks)  # Estimate from chunks
        # Estimate storage based on typical embedding dimensions (1536 for Voyage AI)
        estimated_dim = 1536
        storage_bytes_to_add = vectors_to_add * estimated_dim * 4  # 4 bytes per float32

        # Determine limits (defaults align with Tenant model defaults)
        vector_limit = int(limits.get("vectors", 500000))
        storage_gb_limit = int(limits.get("storage_gb", 100))
        storage_bytes_limit = storage_gb_limit * 1024 * 1024 * 1024

        # Check quotas BEFORE generating embeddings (fail fast)
        if redis_available and limits:
            try:
                allowed_vecs, new_vecs = await quota_service.check_and_increment(
                    tenant_id, "vector_count", vectors_to_add, vector_limit
                )
            except Exception as e:
                logger.error(
                    f"Vector quota check failed for tenant {tenant_id}: {e}",
                    extra={"tenant_id": tenant_id},
                    exc_info=True,
                )
                allowed_vecs = False  # Fail closed for security

            try:
                allowed_storage, new_bytes = await quota_service.check_and_increment(
                    tenant_id, "storage_bytes", storage_bytes_to_add, storage_bytes_limit
                )
            except Exception as e:
                logger.error(
                    f"Storage quota check failed for tenant {tenant_id}: {e}",
                    extra={"tenant_id": tenant_id},
                    exc_info=True,
                )
                allowed_storage = False  # Fail closed for security

            if not allowed_vecs or not allowed_storage:
                # Abort BEFORE expensive embedding generation
                return {
                    "status": "failure",
                    "error": "Quota exceeded",
                    "nodes": 0,
                    "edges": 0,
                    "embeddings": 0,
                    "details": {
                        "vector_limit": vector_limit,
                        "storage_bytes_limit": storage_bytes_limit,
                        "requested_vectors": vectors_to_add,
                        "requested_storage_bytes": storage_bytes_to_add,
                    },
                }

        # 3. Generate embeddings with Voyage AI (40%) - AFTER quota check
        self.update_state(
            state="PROGRESS", meta={"status": "Generating embeddings", "progress": 40}
        )

        embedding_service = EmbeddingService()
        embeddings = await embedding_service.embed_batch(chunks)

        # Estimate embedding tokens consumed (AAET-27)
        # NOTE: This uses a rough approximation (1 token ≈ 4 characters for English text)
        # For production billing, consider using the actual tokenizer from the embedding model
        # to ensure accurate token counts. Different models use different tokenization strategies.
        total_tokens = sum(len(chunk.get("text", "")) // 4 for chunk in chunks)

        # 4. Store nodes (60%)
        self.update_state(state="PROGRESS", meta={"status": "Storing nodes", "progress": 60})

        await store.insert_nodes(tenant_id, result.nodes if hasattr(result, "nodes") else [])

        # 5. Store edges (80%)
        self.update_state(state="PROGRESS", meta={"status": "Storing edges", "progress": 80})

        await store.insert_edges(tenant_id, result.edges if hasattr(result, "edges") else [])

        # 6. Store embeddings (90%)
        self.update_state(state="PROGRESS", meta={"status": "Storing embeddings", "progress": 90})

        embeddings_count = await store.insert_embeddings(tenant_id, repo_id, embeddings)
        # Increment Prometheus metrics on success (AAET-27)
        try:
            vector_count_total.labels(tenant_id=tenant_id).inc(embeddings_count)
            storage_bytes_total.labels(tenant_id=tenant_id).inc(storage_bytes_to_add)
            embedding_tokens_total.labels(tenant_id=tenant_id, operation="file_ingestion").inc(
                total_tokens
            )
        except Exception as e:
            logger.warning(
                f"Failed to record metrics for tenant {tenant_id}: {e}",
                extra={"tenant_id": tenant_id, "error": str(e)},
            )

        # Complete
        self.update_state(state="PROGRESS", meta={"status": "Complete", "progress": 100})

        logger.info(
            "File parse task complete",
            extra={
                "task_id": self.request.id,
                "tenant_id": tenant_id,
                "file_path": file_path,
                "nodes": result.nodes_created,
                "edges": result.edges_created,
                "embeddings": embeddings_count,
            },
        )

        # Clean up storage connection
        if store:
            await store.close()

        return {
            "status": "success",
            "nodes": result.nodes_created,
            "edges": result.edges_created,
            "embeddings": embeddings_count,
        }

    except (TenantValidationError, RepositoryParseError) as e:
        # Validation/parse errors should not be retried
        logger.error(
            f"Parse failed: {e}",
            extra={
                "task_id": self.request.id,
                "tenant_id": tenant_id,
                "file_path": file_path,
            },
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
            "Task exceeded time limit", extra={"task_id": self.request.id, "file_path": file_path}
        )
        return {
            "status": "failure",
            "error": "Task exceeded time limit",
            "nodes": 0,
            "edges": 0,
            "embeddings": 0,
        }

    except (StorageError, ConnectionError, VoyageAPIError, VoyageRateLimitError) as e:
        # These errors will be auto-retried by Celery
        error_type = type(e).__name__
        logger.warning(
            f"Retryable error ({error_type}): {e}",
            extra={
                "task_id": self.request.id,
                "file_path": file_path,
                "retry_count": self.request.retries,
                "error_type": error_type,
            },
        )
        raise

    except Exception as e:
        # Catch-all for unexpected errors
        error_type = type(e).__name__
        logger.error(
            f"Unexpected error ({error_type}): {e}",
            extra={
                "task_id": self.request.id,
                "file_path": file_path,
                "error_type": error_type,
                "tenant_id": tenant_id,
                "repo_id": repo_id,
            },
            exc_info=True,
        )

        # Don't retry unexpected errors - they likely indicate bugs
        # that won't be fixed by retrying
        return {
            "status": "failure",
            "error": f"Unexpected error ({error_type}): {str(e)[:200]}",  # Truncate long errors
            "nodes": 0,
            "edges": 0,
            "embeddings": 0,
        }
    finally:
        # Ensure resources are closed even when exceptions occur
        try:
            if store is not None:
                await store.close()
        except Exception:
            pass
        try:
            if redis_available:
                await redis_manager.close_connections()
        except Exception:
            # Avoid raising on teardown paths
            pass
