"""Logseq Searcher - Search your Logseq pages and journals."""

__version__ = "0.1.0"

from .db import init_db, create_schema, get_connection, get_cursor
from .loader import load_markdown_files, insert_documents, load_logseq_vault
from .search import search, advanced_search, get_document, get_document_count

__all__ = [
    'init_db',
    'create_schema',
    'get_connection',
    'get_cursor',
    'load_markdown_files',
    'insert_documents',
    'load_logseq_vault',
    'search',
    'advanced_search',
    'get_document',
    'get_document_count',
]