"""Search functions for querying documents."""

from .db import get_connection


def search(query: str, limit: int = 10, doc_type: str = None) -> list:
    """Search documents using full-text search.

    Args:
        query: Search terms (space-separated words, all must match).
        limit: Maximum number of results to return.
        doc_type: Optional filter for 'page' or 'journal'.

    Returns:
        List of matching documents with id, filename, doc_type, title, rank, and headline.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT
                    id,
                    filename,
                    doc_type,
                    title,
                    ts_rank(content_tsv, query) AS rank,
                    ts_headline('english', content, query,
                        'StartSel=>>>, StopSel=<<<, MaxWords=50, MinWords=20') AS headline
                FROM documents, plainto_tsquery('english', %s) query
                WHERE content_tsv @@ query
            """

            params = [query]

            if doc_type:
                sql += " AND doc_type = %s"
                params.append(doc_type)

            sql += " ORDER BY rank DESC LIMIT %s"
            params.append(limit)

            cur.execute(sql, params)

            results = []
            for row in cur.fetchall():
                results.append({
                    'id': row[0],
                    'filename': row[1],
                    'doc_type': row[2],
                    'title': row[3],
                    'rank': row[4],
                    'headline': row[5]
                })
            return results
    finally:
        conn.close()


def advanced_search(query: str, limit: int = 10) -> list:
    """Search using websearch syntax.

    Supports:
        - "quoted phrases" for exact matching
        - OR for alternatives
        - - (minus) for exclusion

    Args:
        query: Search query using websearch syntax.
        limit: Maximum number of results to return.

    Returns:
        List of matching documents with id, filename, doc_type, title, rank, and headline.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT
                    id,
                    filename,
                    doc_type,
                    title,
                    ts_rank(content_tsv, query) AS rank,
                    ts_headline('english', content, query,
                        'StartSel=>>>, StopSel=<<<, MaxWords=50, MinWords=20') AS headline
                FROM documents, websearch_to_tsquery('english', %s) query
                WHERE content_tsv @@ query
                ORDER BY rank DESC
                LIMIT %s
            """

            cur.execute(sql, (query, limit))

            results = []
            for row in cur.fetchall():
                results.append({
                    'id': row[0],
                    'filename': row[1],
                    'doc_type': row[2],
                    'title': row[3],
                    'rank': row[4],
                    'headline': row[5]
                })
            return results
    finally:
        conn.close()


def get_document(doc_id: int) -> dict:
    """Retrieve a full document by ID.

    Args:
        doc_id: The document ID.

    Returns:
        Document dictionary with id, filename, doc_type, title, content, or None if not found.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, filename, doc_type, title, content FROM documents WHERE id = %s",
                (doc_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    'id': row[0],
                    'filename': row[1],
                    'doc_type': row[2],
                    'title': row[3],
                    'content': row[4]
                }
            return None
    finally:
        conn.close()


def get_document_count() -> dict:
    """Get count of documents by type.

    Returns:
        Dictionary mapping doc_type to count.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type")
            return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        conn.close()
