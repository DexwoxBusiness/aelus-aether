"""Celery tasks for background processing."""

from .ingestion import parse_and_index_repository

__all__ = ["parse_and_index_repository"]
