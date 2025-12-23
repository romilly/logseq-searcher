"""Search functions for querying documents."""

from .db import get_connection
from .embeddings import generate_embedding


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


def semantic_search(query: str, limit: int = 10, doc_type: str = None) -> list:
    """Search documents using semantic similarity.

    Uses vector embeddings to find documents with similar meaning,
    even if they don't contain the exact query terms.

    Args:
        query: Natural language query.
        limit: Maximum number of results to return.
        doc_type: Optional filter for 'page' or 'journal'.

    Returns:
        List of matching documents with id, filename, doc_type, title, similarity, and snippet.
    """
    # Generate embedding for the query
    query_embedding = generate_embedding(query)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT
                    id,
                    filename,
                    doc_type,
                    title,
                    1 - (embedding <=> %s::vector) AS similarity,
                    LEFT(content, 200) AS snippet
                FROM documents
                WHERE embedding IS NOT NULL
            """

            params = [query_embedding]

            if doc_type:
                sql += " AND doc_type = %s"
                params.append(doc_type)

            sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
            params.extend([query_embedding, limit])

            cur.execute(sql, params)

            results = []
            for row in cur.fetchall():
                results.append({
                    'id': row[0],
                    'filename': row[1],
                    'doc_type': row[2],
                    'title': row[3],
                    'similarity': row[4],
                    'snippet': row[5]
                })
            return results
    finally:
        conn.close()


def hybrid_search(query: str, limit: int = 10, doc_type: str = None,
                  fts_weight: float = 0.5, semantic_weight: float = 0.5) -> list:
    """Search documents using both full-text search and semantic similarity.

    Combines the strengths of keyword matching and semantic understanding.
    Results are ranked by a weighted combination of FTS rank and semantic similarity.

    Args:
        query: Search query (used for both FTS and semantic search).
        limit: Maximum number of results to return.
        doc_type: Optional filter for 'page' or 'journal'.
        fts_weight: Weight for full-text search score (0-1).
        semantic_weight: Weight for semantic similarity score (0-1).

    Returns:
        List of matching documents with id, filename, doc_type, title,
        combined_score, fts_rank, similarity, and headline.
    """
    # Generate embedding for the query
    query_embedding = generate_embedding(query)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Use a CTE to compute both scores, then combine them
            sql = """
                WITH fts_results AS (
                    SELECT
                        id,
                        ts_rank(content_tsv, plainto_tsquery('english', %s)) AS fts_rank
                    FROM documents
                    WHERE content_tsv @@ plainto_tsquery('english', %s)
                ),
                semantic_results AS (
                    SELECT
                        id,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM documents
                    WHERE embedding IS NOT NULL
                ),
                combined AS (
                    SELECT
                        d.id,
                        d.filename,
                        d.doc_type,
                        d.title,
                        d.content,
                        COALESCE(f.fts_rank, 0) AS fts_rank,
                        COALESCE(s.similarity, 0) AS similarity,
                        (COALESCE(f.fts_rank, 0) * %s + COALESCE(s.similarity, 0) * %s) AS combined_score
                    FROM documents d
                    LEFT JOIN fts_results f ON d.id = f.id
                    LEFT JOIN semantic_results s ON d.id = s.id
                    WHERE f.id IS NOT NULL OR s.similarity > 0.3
            """

            params = [query, query, query_embedding, fts_weight, semantic_weight]

            if doc_type:
                sql += " AND d.doc_type = %s"
                params.append(doc_type)

            sql += """
                )
                SELECT
                    id,
                    filename,
                    doc_type,
                    title,
                    combined_score,
                    fts_rank,
                    similarity,
                    ts_headline('english', content, plainto_tsquery('english', %s),
                        'StartSel=>>>, StopSel=<<<, MaxWords=50, MinWords=20') AS headline
                FROM combined
                ORDER BY combined_score DESC
                LIMIT %s
            """
            params.extend([query, limit])

            cur.execute(sql, params)

            results = []
            for row in cur.fetchall():
                results.append({
                    'id': row[0],
                    'filename': row[1],
                    'doc_type': row[2],
                    'title': row[3],
                    'combined_score': row[4],
                    'fts_rank': row[5],
                    'similarity': row[6],
                    'headline': row[7]
                })
            return results
    finally:
        conn.close()
