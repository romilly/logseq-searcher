"""Document loading functions."""

from pathlib import Path

from psycopg2.extras import execute_values

from .db import get_connection
from .embeddings import generate_embeddings


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


def insert_documents(documents: list, with_embeddings: bool = False):
    """Insert documents into the database.

    Args:
        documents: List of document dictionaries with filename, doc_type, title, content.
        with_embeddings: If True, generate and store embeddings for each document.
    """
    if not documents:
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if with_embeddings:
                # Generate embeddings for title + content
                texts = [f"{doc['title']}\n\n{doc['content']}" for doc in documents]
                embeddings = generate_embeddings(texts)

                data = [
                    (doc['filename'], doc['doc_type'], doc['title'], doc['content'], emb)
                    for doc, emb in zip(documents, embeddings)
                ]

                execute_values(
                    cur,
                    "INSERT INTO documents (filename, doc_type, title, content, embedding) VALUES %s",
                    data,
                    page_size=100
                )
            else:
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


def load_logseq_vault(vault_path: Path, with_embeddings: bool = False,
                      batch_size: int = 50, progress_callback=None) -> dict:
    """Load all documents from a Logseq vault.

    Args:
        vault_path: Path to the Logseq vault root directory.
        with_embeddings: If True, generate embeddings for each document.
        batch_size: Number of documents to process at once when generating embeddings.
        progress_callback: Optional callback function(processed, total) for progress updates.

    Returns:
        Dictionary with 'pages', 'journals', and 'total' counts.
    """
    pages = load_markdown_files(vault_path / 'pages', 'page')
    journals = load_markdown_files(vault_path / 'journals', 'journal')

    all_documents = pages + journals
    total = len(all_documents)

    if with_embeddings:
        # Process in batches to avoid overwhelming Ollama
        for i in range(0, total, batch_size):
            batch = all_documents[i:i + batch_size]
            insert_documents(batch, with_embeddings=True)
            if progress_callback:
                progress_callback(min(i + batch_size, total), total)
    else:
        insert_documents(all_documents)
        if progress_callback:
            progress_callback(total, total)

    return {
        'pages': len(pages),
        'journals': len(journals),
        'total': total
    }


def add_embeddings_to_existing(batch_size: int = 50, progress_callback=None):
    """Add embeddings to documents that don't have them.

    Args:
        batch_size: Number of documents to process at once.
        progress_callback: Optional callback function(processed, total) for progress updates.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Count documents without embeddings
            cur.execute("SELECT COUNT(*) FROM documents WHERE embedding IS NULL")
            total = cur.fetchone()[0]

            if total == 0:
                return

            processed = 0
            while True:
                # Fetch a batch of documents without embeddings
                cur.execute("""
                    SELECT id, title, content
                    FROM documents
                    WHERE embedding IS NULL
                    ORDER BY id
                    LIMIT %s
                """, (batch_size,))

                rows = cur.fetchall()
                if not rows:
                    break

                # Generate embeddings
                texts = [f"{row[1]}\n\n{row[2]}" for row in rows]
                embeddings = generate_embeddings(texts)

                # Update documents with embeddings
                for row, embedding in zip(rows, embeddings):
                    cur.execute(
                        "UPDATE documents SET embedding = %s WHERE id = %s",
                        (embedding, row[0])
                    )

                conn.commit()
                processed += len(rows)

                if progress_callback:
                    progress_callback(processed, total)
    finally:
        conn.close()
