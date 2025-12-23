"""Database connection and schema management."""

import os
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv


def load_db_config(env_path: str = None) -> dict:
    """Load database configuration from environment variables.

    Args:
        env_path: Optional path to .env file. If None, uses default dotenv behavior.

    Returns:
        Dictionary with database connection parameters.

    Raises:
        ValueError: If required environment variables are missing.
    """
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', '5432'),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
    }

    missing = [k for k, v in config.items() if not v and k != 'port']
    if missing:
        raise ValueError(f"Missing environment variables: {missing}")

    return config


_db_config = None


def init_db(env_path: str = None):
    """Initialize the database configuration.

    Args:
        env_path: Optional path to .env file.
    """
    global _db_config
    _db_config = load_db_config(env_path)


def get_connection():
    """Create a database connection using the initialized configuration.

    Returns:
        A psycopg2 connection object.

    Raises:
        RuntimeError: If init_db() has not been called.
    """
    if _db_config is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return psycopg2.connect(**_db_config)


@contextmanager
def get_cursor():
    """Context manager for database cursor with automatic commit/rollback.

    Yields:
        A psycopg2 cursor object.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_schema():
    """Create the documents table with full-text search support.

    This will drop any existing documents table and recreate it.
    """
    with get_cursor() as cur:
        # Drop existing table if it exists
        cur.execute("DROP TABLE IF EXISTS documents CASCADE")

        # Create table with tsvector column
        cur.execute("""
            CREATE TABLE documents (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_tsv TSVECTOR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create GIN index for fast full-text search
        cur.execute("""
            CREATE INDEX documents_content_tsv_idx
            ON documents USING GIN (content_tsv)
        """)

        # Create trigger to auto-update tsvector on insert/update
        cur.execute("""
            CREATE OR REPLACE FUNCTION documents_tsv_trigger()
            RETURNS trigger AS $$
            BEGIN
                NEW.content_tsv :=
                    setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B');
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql
        """)

        cur.execute("""
            CREATE TRIGGER documents_tsv_update
            BEFORE INSERT OR UPDATE ON documents
            FOR EACH ROW EXECUTE FUNCTION documents_tsv_trigger()
        """)
