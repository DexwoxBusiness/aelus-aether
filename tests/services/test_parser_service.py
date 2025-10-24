"""Tests for ParserService.

AAET-86: Part 2 - Service Layer Tests
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ingestion.parser_service import (
    ParseResult,
    ParserService,
    RepositoryParseError,
    TenantValidationError,
)


class TestParseResult:
    """Tests for ParseResult class."""

    def test_success_result(self):
        """Test creating a successful parse result."""
        result = ParseResult(
            success=True,
            parse_time_seconds=1.234,
            nodes_created=100,
            edges_created=50,
        )

        assert result.success is True
        assert result.parse_time_seconds == 1.234
        assert result.nodes_created == 100
        assert result.edges_created == 50
        assert result.error is None

    def test_failure_result(self):
        """Test creating a failed parse result."""
        result = ParseResult(success=False, parse_time_seconds=0.5, error="Something went wrong")

        assert result.success is False
        assert result.parse_time_seconds == 0.5
        assert result.nodes_created == 0
        assert result.edges_created == 0
        assert result.error == "Something went wrong"

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = ParseResult(
            success=True,
            parse_time_seconds=1.234567,
            nodes_created=100,
            edges_created=50,
        )

        result_dict = result.to_dict()

        assert result_dict == {
            "success": True,
            "nodes_created": 100,
            "edges_created": 50,
            "parse_time_seconds": 1.235,  # Rounded to 3 decimals
        }

    def test_to_dict_with_error(self):
        """Test converting failed result to dictionary."""
        result = ParseResult(success=False, parse_time_seconds=0.5, error="Test error")

        result_dict = result.to_dict()

        assert result_dict["success"] is False
        assert result_dict["error"] == "Test error"


class TestParserService:
    """Tests for ParserService class."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock storage interface."""
        store = AsyncMock()
        store.set_tenant_id = MagicMock()
        store.count_nodes = AsyncMock(return_value=0)
        store.count_edges = AsyncMock(return_value=0)
        return store

    @pytest.fixture
    def service(self, mock_store):
        """Create a ParserService instance with mock store."""
        return ParserService(mock_store)

    def test_init(self, mock_store):
        """Test service initialization."""
        service = ParserService(mock_store)
        assert service.store == mock_store

    def test_validate_tenant_id_valid(self, service):
        """Test tenant_id validation with valid input."""
        # Should not raise
        service._validate_tenant_id("tenant-123")

    def test_validate_tenant_id_empty(self, service):
        """Test tenant_id validation with empty string."""
        with pytest.raises(TenantValidationError, match="tenant_id is required"):
            service._validate_tenant_id("")

    def test_validate_tenant_id_whitespace(self, service):
        """Test tenant_id validation with whitespace."""
        with pytest.raises(TenantValidationError, match="tenant_id is required"):
            service._validate_tenant_id("   ")

    def test_validate_tenant_id_none(self, service):
        """Test tenant_id validation with None."""
        with pytest.raises(TenantValidationError, match="tenant_id is required"):
            service._validate_tenant_id(None)

    def test_validate_repo_id_valid(self, service):
        """Test repo_id validation with valid input."""
        # Should not raise
        service._validate_repo_id("repo-456")

    def test_validate_repo_id_empty(self, service):
        """Test repo_id validation with empty string."""
        with pytest.raises(TenantValidationError, match="repo_id is required"):
            service._validate_repo_id("")

    def test_validate_repo_path_valid(self, service, tmp_path):
        """Test repo_path validation with valid directory."""
        result = service._validate_repo_path(tmp_path)
        assert result == tmp_path
        assert isinstance(result, Path)

    def test_validate_repo_path_string(self, service, tmp_path):
        """Test repo_path validation with string path."""
        result = service._validate_repo_path(str(tmp_path))
        assert result == tmp_path
        assert isinstance(result, Path)

    def test_validate_repo_path_not_exists(self, service):
        """Test repo_path validation with non-existent path."""
        with pytest.raises(RepositoryParseError, match="does not exist"):
            service._validate_repo_path("/nonexistent/path")

    def test_validate_repo_path_not_directory(self, service, tmp_path):
        """Test repo_path validation with file instead of directory."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")

        with pytest.raises(RepositoryParseError, match="not a directory"):
            service._validate_repo_path(file_path)

    @pytest.mark.asyncio
    async def test_parse_repository_validation_errors(self, service, tmp_path):
        """Test parse_repository with validation errors."""
        # Test empty tenant_id
        with pytest.raises(TenantValidationError):
            await service.parse_repository("", "repo-1", tmp_path)

        # Test empty repo_id
        with pytest.raises(TenantValidationError):
            await service.parse_repository("tenant-1", "", tmp_path)

        # Test invalid path
        with pytest.raises(RepositoryParseError):
            await service.parse_repository("tenant-1", "repo-1", "/nonexistent")

    @pytest.mark.asyncio
    @patch("services.ingestion.parser_service.GraphUpdater")
    async def test_parse_repository_success(self, mock_updater_class, service, tmp_path):
        """Test successful repository parse."""
        # Setup mock
        mock_updater = AsyncMock()
        mock_updater.run = AsyncMock()
        mock_updater_class.return_value = mock_updater

        # Execute
        result = await service.parse_repository(
            tenant_id="tenant-123", repo_id="repo-456", repo_path=tmp_path
        )

        # Verify
        assert result.success is True
        assert result.parse_time_seconds > 0
        assert result.error is None

        # Verify store.set_tenant_id was called
        service.store.set_tenant_id.assert_called_once_with("tenant-123")

        # Verify GraphUpdater was created with correct params
        mock_updater_class.assert_called_once()
        call_kwargs = mock_updater_class.call_args.kwargs
        assert call_kwargs["tenant_id"] == "tenant-123"
        assert call_kwargs["repo_id"] == "repo-456"
        assert call_kwargs["repo_path"] == tmp_path

        # Verify run was called
        mock_updater.run.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.ingestion.parser_service.GraphUpdater")
    async def test_parse_repository_storage_error(self, mock_updater_class, service, tmp_path):
        """Test parse_repository with storage error."""
        from libs.code_graph_rag.storage.postgres_store import StorageError

        # Setup mock to raise StorageError
        mock_updater = AsyncMock()
        mock_updater.run = AsyncMock(side_effect=StorageError("Database connection failed"))
        mock_updater_class.return_value = mock_updater

        # Execute
        result = await service.parse_repository(
            tenant_id="tenant-123", repo_id="repo-456", repo_path=tmp_path
        )

        # Verify error handling
        assert result.success is False
        assert "Storage error" in result.error
        assert "Database connection failed" in result.error
        assert result.parse_time_seconds > 0

    @pytest.mark.asyncio
    @patch("services.ingestion.parser_service.GraphUpdater")
    async def test_parse_repository_unexpected_error(self, mock_updater_class, service, tmp_path):
        """Test parse_repository with unexpected error."""
        # Setup mock to raise unexpected error
        mock_updater = AsyncMock()
        mock_updater.run = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        mock_updater_class.return_value = mock_updater

        # Execute
        result = await service.parse_repository(
            tenant_id="tenant-123", repo_id="repo-456", repo_path=tmp_path
        )

        # Verify error handling
        assert result.success is False
        assert "Unexpected error" in result.error
        assert result.parse_time_seconds > 0
