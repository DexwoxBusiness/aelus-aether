"""Tests for ingestion Celery tasks.

AAET-87: Celery Integration Tests
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ingestion.parser_service import ParseResult
from workers.tasks.ingestion import parse_and_index_file


class TestParseAndIndexFile:
    """Tests for parse_and_index_file task."""

    @pytest.fixture
    def mock_store(self):
        """Create mock storage."""
        store = MagicMock()
        store.connect = AsyncMock()
        store.close = AsyncMock()
        store.set_tenant_id = MagicMock()
        store.count_nodes = AsyncMock(return_value=100)
        store.count_edges = AsyncMock(return_value=50)
        return store

    @pytest.fixture
    def mock_parse_result(self):
        """Create mock parse result."""
        return ParseResult(
            success=True, parse_time_seconds=2.5, nodes_created=100, edges_created=50
        )

    @pytest.mark.asyncio
    @patch("workers.tasks.ingestion.PostgresGraphStore")
    @patch("workers.tasks.ingestion.ParserService")
    @patch("workers.tasks.ingestion.EmbeddingService")
    async def test_task_success(
        self, mock_embed_class, mock_service_class, mock_store_class, mock_store, mock_parse_result
    ):
        """Test successful task execution."""
        # Setup mocks
        mock_store_class.return_value = mock_store

        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(return_value=mock_parse_result)
        mock_service_class.return_value = mock_service

        mock_embed_service = MagicMock()
        mock_embed_service.embed_batch = AsyncMock(
            return_value=[{"chunk_id": "chunk_0", "embedding": [0.1] * 1024, "metadata": {}}]
        )
        mock_embed_class.return_value = mock_embed_service

        # Mock store methods
        mock_store.insert_nodes = AsyncMock()
        mock_store.insert_edges = AsyncMock()
        mock_store.insert_embeddings = AsyncMock(return_value=1)

        # Mock the Celery task instance
        mock_task = MagicMock()
        mock_task.request.id = "test-task-id"
        mock_task.update_state = MagicMock()

        # Execute task by calling the underlying function directly
        # Use __wrapped__ to bypass Celery decorator
        result = await parse_and_index_file.__wrapped__(
            mock_task,
            tenant_id="tenant-123",
            repo_id="repo-456",
            file_path="src/main.py",
            file_content="def hello(): pass",
            language="python",
            connection_string="postgresql://test",
        )

        # Verify result
        assert result["status"] == "success"
        assert result["nodes"] == 100
        assert result["edges"] == 50
        assert result["embeddings"] == 1

        # Verify store was connected and closed
        mock_store.connect.assert_called_once()
        mock_store.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("workers.tasks.ingestion.PostgresGraphStore")
    @patch("workers.tasks.ingestion.ParserService")
    async def test_task_validation_error(self, mock_service_class, mock_store_class, mock_store):
        """Test task with validation error (no retry)."""
        from services.ingestion.parser_service import TenantValidationError

        # Setup mocks
        mock_store_class.return_value = mock_store

        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(side_effect=TenantValidationError("Invalid tenant"))
        mock_service_class.return_value = mock_service

        # Mock the Celery task instance
        mock_task = MagicMock()
        mock_task.request.id = "test-task-id"
        mock_task.update_state = MagicMock()

        # Execute task
        result = await parse_and_index_file.__wrapped__(
            mock_task,
            tenant_id="",
            repo_id="repo-456",
            file_path="src/main.py",
            file_content="code",
            language="python",
            connection_string="postgresql://test",
        )

        # Verify error result
        assert result["status"] == "failure"
        assert "Invalid tenant" in result["error"]
        assert result["nodes"] == 0
        assert result["edges"] == 0

    @pytest.mark.asyncio
    @patch("workers.tasks.ingestion.PostgresGraphStore")
    @patch("workers.tasks.ingestion.ParserService")
    async def test_task_parse_error(self, mock_service_class, mock_store_class, mock_store):
        """Test task with parse error (no retry)."""
        from services.ingestion.parser_service import RepositoryParseError

        # Setup mocks
        mock_store_class.return_value = mock_store

        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(side_effect=RepositoryParseError("Invalid file"))
        mock_service_class.return_value = mock_service

        # Mock the Celery task instance
        mock_task = MagicMock()
        mock_task.request.id = "test-task-id"
        mock_task.update_state = MagicMock()

        # Execute task
        result = await parse_and_index_file.__wrapped__(
            mock_task,
            tenant_id="tenant-123",
            repo_id="repo-456",
            file_path="bad.py",
            file_content="invalid",
            language="python",
            connection_string="postgresql://test",
        )

        # Verify error result
        assert result["status"] == "failure"
        assert "Invalid file" in result["error"]

    @pytest.mark.asyncio
    @patch("workers.tasks.ingestion.PostgresGraphStore")
    async def test_task_storage_error_retries(self, mock_store_class, mock_store):
        """Test task retries on storage error."""
        from libs.code_graph_rag.storage.postgres_store import StorageError

        # Setup mock to raise StorageError
        mock_store.connect = AsyncMock(side_effect=StorageError("Connection failed"))
        mock_store_class.return_value = mock_store

        # Mock the Celery task instance
        mock_task = MagicMock()
        mock_task.request.id = "test-task-id"
        mock_task.update_state = MagicMock()

        # Execute task - should raise StorageError for retry
        with pytest.raises(StorageError):
            await parse_and_index_file.__wrapped__(
                mock_task,
                tenant_id="tenant-123",
                repo_id="repo-456",
                file_path="src/main.py",
                file_content="code",
                language="python",
                connection_string="postgresql://test",
            )

    @pytest.mark.asyncio
    @patch("workers.tasks.ingestion.PostgresGraphStore")
    @patch("workers.tasks.ingestion.ParserService")
    @patch("workers.tasks.ingestion.EmbeddingService")
    async def test_task_voyage_rate_limit_retries(
        self, mock_embed_class, mock_service_class, mock_store_class, mock_store, mock_parse_result
    ):
        """Test task retries on Voyage API rate limit."""
        from services.ingestion.embedding_service import VoyageRateLimitError

        # Setup mocks
        mock_store_class.return_value = mock_store

        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(return_value=mock_parse_result)
        mock_service_class.return_value = mock_service

        mock_embed_service = MagicMock()
        mock_embed_service.embed_batch = AsyncMock(
            side_effect=VoyageRateLimitError("Rate limit exceeded")
        )
        mock_embed_class.return_value = mock_embed_service

        # Mock the Celery task instance
        mock_task = MagicMock()
        mock_task.request.id = "test-task-id"
        mock_task.update_state = MagicMock()

        # Execute task - should raise VoyageRateLimitError for retry
        with pytest.raises(VoyageRateLimitError):
            await parse_and_index_file.__wrapped__(
                mock_task,
                tenant_id="tenant-123",
                repo_id="repo-456",
                file_path="src/main.py",
                file_content="code",
                language="python",
                connection_string="postgresql://test",
            )

    @pytest.mark.asyncio
    @patch("workers.tasks.ingestion.PostgresGraphStore")
    @patch("workers.tasks.ingestion.ParserService")
    @patch("workers.tasks.ingestion.EmbeddingService")
    async def test_task_voyage_api_error_retries(
        self, mock_embed_class, mock_service_class, mock_store_class, mock_store, mock_parse_result
    ):
        """Test task retries on Voyage API error."""
        from services.ingestion.embedding_service import VoyageAPIError

        # Setup mocks
        mock_store_class.return_value = mock_store

        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(return_value=mock_parse_result)
        mock_service_class.return_value = mock_service

        mock_embed_service = MagicMock()
        mock_embed_service.embed_batch = AsyncMock(side_effect=VoyageAPIError("API error 500"))
        mock_embed_class.return_value = mock_embed_service

        # Mock the Celery task instance
        mock_task = MagicMock()
        mock_task.request.id = "test-task-id"
        mock_task.update_state = MagicMock()

        # Execute task - should raise VoyageAPIError for retry
        with pytest.raises(VoyageAPIError):
            await parse_and_index_file.__wrapped__(
                mock_task,
                tenant_id="tenant-123",
                repo_id="repo-456",
                file_path="src/main.py",
                file_content="code",
                language="python",
                connection_string="postgresql://test",
            )

    @pytest.mark.asyncio
    @patch("workers.tasks.ingestion.PostgresGraphStore")
    @patch("workers.tasks.ingestion.ParserService")
    async def test_task_unexpected_error(self, mock_service_class, mock_store_class, mock_store):
        """Test task with unexpected error."""
        # Setup mocks
        mock_store_class.return_value = mock_store

        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        mock_service_class.return_value = mock_service

        # Mock the Celery task instance
        mock_task = MagicMock()
        mock_task.request.id = "test-task-id"
        mock_task.update_state = MagicMock()

        # Execute task
        result = await parse_and_index_file.__wrapped__(
            mock_task,
            tenant_id="tenant-123",
            repo_id="repo-456",
            file_path="src/main.py",
            file_content="code",
            language="python",
            connection_string="postgresql://test",
        )

        # Verify error result
        assert result["status"] == "failure"
        assert "Unexpected error" in result["error"]
