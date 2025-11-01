"""Parser service wrapper for code-graph-rag library.

This service wraps the code-graph-rag library with aelus-aether specific
functionality including tenant context, error handling, metrics collection,
and structured logging.

AAET-86: Part 2 - Service Layer Wrapper
"""

import logging
import time
from pathlib import Path
from typing import Any, Protocol

from libs.code_graph_rag.graph_builder import GraphUpdater
from libs.code_graph_rag.storage.interface import StorageError


class TenantAwareStore(Protocol):
    """Graph store that supports setting tenant context at runtime.

    Extends the upstream GraphStoreInterface with set_tenant_id used by our
    service layer, so mypy understands this attribute exists on our concrete stores.
    """

    def set_tenant_id(self, tenant_id: str) -> None: ...
    async def count_nodes(self, tenant_id: str, repo_id: str) -> int: ...
    async def count_edges(self, tenant_id: str, repo_id: str) -> int: ...


logger = logging.getLogger(__name__)


class ParserServiceError(Exception):
    """Base exception for parser service errors."""

    pass


class TenantValidationError(ParserServiceError):
    """Raised when tenant validation fails."""

    pass


class RepositoryParseError(ParserServiceError):
    """Raised when repository parsing fails."""

    pass


class ParseResult:
    """Result of a repository parse operation.

    Attributes:
        success: Whether the parse was successful
        nodes_created: Number of nodes created (placeholder)
        edges_created: Number of edges created (placeholder)
        parse_time_seconds: Time taken to parse in seconds
        error: Error message if parse failed
    """

    def __init__(
        self,
        success: bool,
        parse_time_seconds: float,
        nodes_created: int = 0,
        edges_created: int = 0,
        error: str | None = None,
    ):
        self.success = success
        self.nodes_created = nodes_created
        self.edges_created = edges_created
        self.parse_time_seconds = parse_time_seconds
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        result: dict[str, Any] = {
            "success": self.success,
            "nodes_created": self.nodes_created,
            "edges_created": self.edges_created,
            "parse_time_seconds": round(self.parse_time_seconds, 3),
        }
        if self.error:
            result["error"] = self.error
        return result


class ParserService:
    """Service layer for code parsing with tenant context and metrics.

    This service wraps the code-graph-rag GraphUpdater with aelus-aether
    specific functionality:
    - Tenant context validation and injection
    - Error handling with proper exceptions
    - Metrics collection (parse time, node/edge counts)
    - Structured logging with tenant context
    - Quota validation (placeholder)

    Example:
        ```python
        from services.ingestion import ParserService
        from libs.code_graph_rag.storage import PostgresGraphStore

        store = PostgresGraphStore(connection_string)
        await store.connect()

        service = ParserService(store)
        result = await service.parse_repository(
            tenant_id="tenant-123",
            repo_id="repo-456",
            repo_path="/path/to/repo"
        )

        print(f"Parsed in {result.parse_time_seconds}s")
        print(f"Created {result.nodes_created} nodes, {result.edges_created} edges")
        ```
    """

    def __init__(self, store: TenantAwareStore):
        """Initialize the parser service.

        Args:
            store: Graph storage interface (must support async operations)
        """
        self.store = store

    async def parse_file(
        self, tenant_id: str, repo_id: str, file_path: str, file_content: str, language: str
    ) -> ParseResult:
        """Parse a single file and build its code graph.

        This method parses a single file in memory without requiring
        the full repository on disk. Useful for:
        - Real-time parsing of uploaded files
        - Incremental updates when files change
        - API-driven parsing workflows

        Args:
            tenant_id: Tenant identifier for multi-tenant isolation
            repo_id: Repository identifier
            file_path: Path to file (for context, doesn't need to exist)
            file_content: Content of the file to parse
            language: Programming language (python, typescript, java, etc.)

        Returns:
            ParseResult with success status, metrics, and optional error

        Raises:
            TenantValidationError: If tenant_id or repo_id is invalid
            RepositoryParseError: If parsing fails

        Note:
            This is a simplified version that parses a single file.
            For full repository parsing with dependencies, use parse_repository().
        """
        start_time = time.time()

        # Validate inputs
        self._validate_tenant_id(tenant_id)
        self._validate_repo_id(repo_id)

        if not language or not language.strip():
            raise RepositoryParseError("language is required and cannot be empty")

        # Log start with tenant context
        logger.info(
            "Starting file parse",
            extra={
                "tenant_id": tenant_id,
                "repo_id": repo_id,
                "file_path": file_path,
                "language": language,
            },
        )

        try:
            # Set tenant context in storage
            self.store.set_tenant_id(tenant_id)

            # TODO: Implement single-file parsing
            # For now, raise NotImplementedError with helpful message
            raise NotImplementedError(
                "Single-file parsing not yet implemented. "
                "Use parse_repository() for full repository parsing. "
                "This method will be implemented in a future update to support "
                "real-time file parsing without requiring the full repository."
            )

        except NotImplementedError:
            # Re-raise NotImplementedError as-is
            raise

        except Exception as e:
            # Unexpected errors
            parse_time = time.time() - start_time
            error_msg = f"Unexpected error during file parse: {e}"

            logger.error(
                error_msg,
                extra={
                    "tenant_id": tenant_id,
                    "repo_id": repo_id,
                    "file_path": file_path,
                    "language": language,
                    "parse_time_seconds": round(parse_time, 3),
                },
                exc_info=True,
            )

            return ParseResult(success=False, parse_time_seconds=parse_time, error=error_msg)

    async def parse_repository(
        self,
        tenant_id: str,
        repo_id: str,
        repo_path: str | Path,
    ) -> ParseResult:
        """Parse a repository and build its code graph.

        This method:
        1. Validates tenant_id and repo_id
        2. Sets tenant context in storage
        3. Creates GraphUpdater with tenant context
        4. Runs parsing (tenant_id flows to all nodes/edges via AAET-86 Part 1)
        5. Collects metrics and logs results

        Args:
            tenant_id: Tenant identifier for multi-tenant isolation
            repo_id: Repository identifier
            repo_path: Path to repository root directory

        Returns:
            ParseResult with success status, metrics, and optional error

        Raises:
            TenantValidationError: If tenant_id or repo_id is invalid
            RepositoryParseError: If parsing fails
        """
        start_time = time.time()

        # Validate inputs
        self._validate_tenant_id(tenant_id)
        self._validate_repo_id(repo_id)
        repo_path = self._validate_repo_path(repo_path)

        # Log start with tenant context
        logger.info(
            "Starting repository parse",
            extra={"tenant_id": tenant_id, "repo_id": repo_id, "repo_path": str(repo_path)},
        )

        try:
            # Set tenant context in storage
            self.store.set_tenant_id(tenant_id)

            # TODO: Validate tenant quotas (placeholder)
            # await self._validate_tenant_quotas(tenant_id)

            # Create GraphUpdater with tenant context
            # Note: parsers and queries will be loaded from config in production
            updater = GraphUpdater(
                tenant_id=tenant_id,
                repo_id=repo_id,
                store=self.store,
                repo_path=repo_path,
                parsers=self._get_parsers(),  # TODO: Load from config
                queries=self._get_queries(),  # TODO: Load from config
            )

            # Run parsing - tenant_id flows to all nodes/edges automatically
            await updater.run()

            # Calculate metrics
            parse_time = time.time() - start_time

            # Get actual counts from storage (AAET-86: Fixed - no longer placeholders)
            nodes_created = await self.store.count_nodes(tenant_id, repo_id)
            edges_created = await self.store.count_edges(tenant_id, repo_id)

            # Log success
            logger.info(
                "Repository parse complete",
                extra={
                    "tenant_id": tenant_id,
                    "repo_id": repo_id,
                    "parse_time_seconds": round(parse_time, 3),
                    "nodes_created": nodes_created,
                    "edges_created": edges_created,
                },
            )

            return ParseResult(
                success=True,
                parse_time_seconds=parse_time,
                nodes_created=nodes_created,
                edges_created=edges_created,
            )

        except StorageError as e:
            # Storage-specific errors
            parse_time = time.time() - start_time
            error_msg = f"Storage error during parse: {e}"

            logger.error(
                error_msg,
                extra={
                    "tenant_id": tenant_id,
                    "repo_id": repo_id,
                    "parse_time_seconds": round(parse_time, 3),
                },
                exc_info=True,
            )

            return ParseResult(success=False, parse_time_seconds=parse_time, error=error_msg)

        except Exception as e:
            # Unexpected errors
            parse_time = time.time() - start_time
            error_msg = f"Unexpected error during parse: {e}"

            logger.error(
                error_msg,
                extra={
                    "tenant_id": tenant_id,
                    "repo_id": repo_id,
                    "parse_time_seconds": round(parse_time, 3),
                },
                exc_info=True,
            )

            return ParseResult(success=False, parse_time_seconds=parse_time, error=error_msg)

    def _validate_tenant_id(self, tenant_id: str) -> None:
        """Validate tenant_id format and value.

        Args:
            tenant_id: Tenant identifier to validate

        Raises:
            TenantValidationError: If tenant_id is invalid
        """
        if not tenant_id or not tenant_id.strip():
            raise TenantValidationError("tenant_id is required and cannot be empty")

        # TODO: Add additional validation (format, existence, etc.)
        # For now, just check it's not empty

    def _validate_repo_id(self, repo_id: str) -> None:
        """Validate repo_id format and value.

        Args:
            repo_id: Repository identifier to validate

        Raises:
            TenantValidationError: If repo_id is invalid
        """
        if not repo_id or not repo_id.strip():
            raise TenantValidationError("repo_id is required and cannot be empty")

        # TODO: Add additional validation (format, existence, etc.)

    def _validate_repo_path(self, repo_path: str | Path) -> Path:
        """Validate repository path exists and is a directory.

        Args:
            repo_path: Path to repository

        Returns:
            Validated Path object

        Raises:
            RepositoryParseError: If path is invalid
        """
        path = Path(repo_path) if isinstance(repo_path, str) else repo_path

        if not path.exists():
            raise RepositoryParseError(f"Repository path does not exist: {path}")

        if not path.is_dir():
            raise RepositoryParseError(f"Repository path is not a directory: {path}")

        return path

    def _get_parsers(self) -> dict[str, Any]:
        """Get parser configuration for all supported languages.

        TODO: Load from configuration file or database.

        Returns:
            Parser configuration dictionary
        """
        # Placeholder - in production, load from config
        return {}

    def _get_queries(self) -> dict[str, Any]:
        """Get query configuration for parsers.

        TODO: Load from configuration file or database.

        Returns:
            Query configuration dictionary
        """
        # Placeholder - in production, load from config
        return {}

    async def _validate_tenant_quotas(self, tenant_id: str) -> None:
        """Validate tenant has not exceeded quotas.

        TODO: Implement quota checking against tenant limits.

        Args:
            tenant_id: Tenant identifier

        Raises:
            TenantValidationError: If tenant has exceeded quotas
        """
        # Placeholder for future quota validation
        # In production, check:
        # - Number of repositories
        # - Total nodes/edges
        # - Storage size
        # - API rate limits
        pass
