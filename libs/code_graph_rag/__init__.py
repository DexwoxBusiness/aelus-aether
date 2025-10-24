"""
code-graph-rag library - Extracted for aelus-aether integration.

This library provides multi-language AST parsing and graph construction
capabilities extracted from the code-graph-rag open-source project.

Original: https://github.com/vitali87/code-graph-rag

Usage:
    from libs.code_graph_rag.parsers.factory import ParserFactory
    from libs.code_graph_rag.graph_builder import GraphUpdater
    from libs.code_graph_rag import language_config

    # Create parser for a language
    parser = ParserFactory.create("python")

    # Parse file
    result = parser.parse(file_content, file_path)
"""

__version__ = "0.1.0"

# Public API exports
from .language_config import LANGUAGE_CONFIGS, get_language_config, get_language_config_by_name
from .parsers.factory import ParserFactory
from .schemas import CodeSnippet, GraphData
from .storage import GraphStoreInterface, PostgresGraphStore

__all__ = [
    "ParserFactory",
    "LANGUAGE_CONFIGS",
    "get_language_config",
    "get_language_config_by_name",
    "GraphData",
    "CodeSnippet",
    "GraphStoreInterface",
    "PostgresGraphStore",
]
