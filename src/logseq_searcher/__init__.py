"""Logseq Searcher - Search your Logseq pages and journals."""

__version__ = "0.1.0"

from .db import init_db, create_schema, get_connection, get_cursor, EMBEDDING_DIM
from .embeddings import init_ollama, generate_embedding, generate_embeddings
from .loader import (
    load_markdown_files,
    insert_documents,
    load_logseq_vault,
    add_embeddings_to_existing,
)
from .search import (
    search,
    advanced_search,
    get_document,
    get_document_count,
    semantic_search,
    hybrid_search,
)

__all__ = [
    # Database
    'init_db',
    'create_schema',
    'get_connection',
    'get_cursor',
    'EMBEDDING_DIM',
    # Embeddings
    'init_ollama',
    'generate_embedding',
    'generate_embeddings',
    # Loading
    'load_markdown_files',
    'insert_documents',
    'load_logseq_vault',
    'add_embeddings_to_existing',
    # Search
    'search',
    'advanced_search',
    'get_document',
    'get_document_count',
    'semantic_search',
    'hybrid_search',
]