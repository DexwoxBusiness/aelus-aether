"""Tests for ingestion Celery tasks.

AAET-87: Celery Integration Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from celery.exceptions import Retry

from workers.tasks.ingestion import parse_and_index_file
from services.ingestion.parser_service import ParseResult


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
            success=True,
            parse_time_seconds=2.5,
            nodes_created=100,
            edges_created=50
        )
    
    @patch('workers.tasks.ingestion.PostgresGraphStore')
    @patch('workers.tasks.ingestion.ParserService')
    @patch('workers.tasks.ingestion.EmbeddingService')
    def test_task_success(self, mock_embed_class, mock_service_class, mock_store_class, mock_store, mock_parse_result):
        """Test successful task execution."""
        # Setup mocks
        mock_store_class.return_value = mock_store
        
        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(return_value=mock_parse_result)
        mock_service_class.return_value = mock_service
        
        mock_embed_service = MagicMock()
        mock_embed_service.generate_embeddings = AsyncMock(return_value=[])
        mock_embed_class.return_value = mock_embed_service
        
        # Execute task
        result = parse_and_index_file(
            tenant_id="tenant-123",
            repo_id="repo-456",
            file_path="src/main.py",
            file_content="def hello(): pass",
            language="python",
            connection_string="postgresql://test"
        )
        
        # Verify result
        assert result["status"] == "success"
        assert result["nodes"] == 100
        assert result["edges"] == 50
        assert result["embeddings"] == 0
        
        # Verify store was connected and closed
        mock_store.connect.assert_called_once()
        mock_store.close.assert_called_once()
    
    @patch('workers.tasks.ingestion.PostgresGraphStore')
    @patch('workers.tasks.ingestion.ParserService')
    def test_task_validation_error(self, mock_service_class, mock_store_class, mock_store):
        """Test task with validation error (no retry)."""
        from services.ingestion.parser_service import TenantValidationError
        
        # Setup mocks
        mock_store_class.return_value = mock_store
        
        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(
            side_effect=TenantValidationError("Invalid tenant")
        )
        mock_service_class.return_value = mock_service
        
        # Execute task
        result = parse_and_index_file(
            tenant_id="",
            repo_id="repo-456",
            file_path="src/main.py",
            file_content="code",
            language="python",
            connection_string="postgresql://test"
        )
        
        # Verify error result
        assert result["status"] == "failure"
        assert "Invalid tenant" in result["error"]
        assert result["nodes"] == 0
        assert result["edges"] == 0
    
    @patch('workers.tasks.ingestion.PostgresGraphStore')
    @patch('workers.tasks.ingestion.ParserService')
    def test_task_parse_error(self, mock_service_class, mock_store_class, mock_store):
        """Test task with parse error (no retry)."""
        from services.ingestion.parser_service import RepositoryParseError
        
        # Setup mocks
        mock_store_class.return_value = mock_store
        
        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(
            side_effect=RepositoryParseError("Invalid file")
        )
        mock_service_class.return_value = mock_service
        
        # Execute task
        result = parse_and_index_file(
            tenant_id="tenant-123",
            repo_id="repo-456",
            file_path="bad.py",
            file_content="invalid",
            language="python",
            connection_string="postgresql://test"
        )
        
        # Verify error result
        assert result["status"] == "failure"
        assert "Invalid file" in result["error"]
    
    @patch('workers.tasks.ingestion.PostgresGraphStore')
    def test_task_storage_error_retries(self, mock_store_class, mock_store):
        """Test task retries on storage error."""
        from libs.code_graph_rag.storage.postgres_store import StorageError
        
        # Setup mock to raise StorageError
        mock_store.connect = AsyncMock(side_effect=StorageError("Connection failed"))
        mock_store_class.return_value = mock_store
        
        # Execute task - should raise StorageError for retry
        with pytest.raises(StorageError):
            parse_and_index_file(
                tenant_id="tenant-123",
                repo_id="repo-456",
                file_path="src/main.py",
                file_content="code",
                language="python",
                connection_string="postgresql://test"
            )
    
    @patch('workers.tasks.ingestion.PostgresGraphStore')
    @patch('workers.tasks.ingestion.ParserService')
    def test_task_unexpected_error(self, mock_service_class, mock_store_class, mock_store):
        """Test task with unexpected error."""
        # Setup mocks
        mock_store_class.return_value = mock_store
        
        mock_service = MagicMock()
        mock_service.parse_file = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )
        mock_service_class.return_value = mock_service
        
        # Execute task
        result = parse_and_index_file(
            tenant_id="tenant-123",
            repo_id="repo-456",
            file_path="src/main.py",
            file_content="code",
            language="python",
            connection_string="postgresql://test"
        )
        
        # Verify error result
        assert result["status"] == "failure"
        assert "Unexpected error" in result["error"]
