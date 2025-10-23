"""Celery tasks for background processing."""

from .ingestion import parse_and_index_file

__all__ = ["parse_and_index_file"]
