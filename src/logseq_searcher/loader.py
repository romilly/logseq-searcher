"""Document loading functions."""

from pathlib import Path

from psycopg2.extras import execute_values

from .db import get_connection


def load_markdown_files(directory: Path, doc_type: str) -> list:
    """Load all markdown files from a directory.

    Args:
        directory: Path to directory containing markdown files.
        doc_type: Type label for the documents (e.g., 'page', 'journal').

    Returns:
        List of document dictionaries with filename, doc_type, title, and content.
    """
    documents = []

    for md_file in directory.glob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
            # Remove NUL bytes - PostgreSQL doesn't allow them in text fields
            content = content.replace('\x00', '')
            # Title is the filename without extension
            title = md_file.stem
            documents.append({
                'filename': md_file.name,
                'doc_type': doc_type,
                'title': title,
                'content': content
            })
        except Exception as e:
            print(f"Error reading {md_file}: {e}")

    return documents


def insert_documents(documents: list):
    """Insert documents into the database.

    Args:
        documents: List of document dictionaries with filename, doc_type, title, content.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            data = [
                (doc['filename'], doc['doc_type'], doc['title'], doc['content'])
                for doc in documents
            ]

            execute_values(
                cur,
                "INSERT INTO documents (filename, doc_type, title, content) VALUES %s",
                data,
                page_size=500
            )

            conn.commit()
    finally:
        conn.close()


def load_logseq_vault(vault_path: Path) -> dict:
    """Load all documents from a Logseq vault.

    Args:
        vault_path: Path to the Logseq vault root directory.

    Returns:
        Dictionary with 'pages', 'journals', and 'total' counts.
    """
    pages = load_markdown_files(vault_path / 'pages', 'page')
    journals = load_markdown_files(vault_path / 'journals', 'journal')

    all_documents = pages + journals
    insert_documents(all_documents)

    return {
        'pages': len(pages),
        'journals': len(journals),
        'total': len(all_documents)
    }
