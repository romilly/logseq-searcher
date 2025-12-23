# logseq-searcher

Search your Logseq pages and journals using full-text search, semantic search, or a hybrid of both.

## Features

- **Full-Text Search**: Fast keyword matching with PostgreSQL's built-in FTS
- **Semantic Search**: Find conceptually related documents using vector embeddings
- **Hybrid Search**: Combine keyword and semantic matching for best results

## Prerequisites

- Python 3.8+
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) extension
- [Ollama](https://ollama.ai/) with `nomic-embed-text` model (for semantic search)

## Installation

1. Clone the repository and create a virtual environment:

```bash
git clone https://github.com/username/logseq-searcher.git
cd logseq-searcher
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Install the package in development mode:

```bash
pip install -e .
```

4. Create a `.env` file in the project root:

```
DB_HOST=your_postgres_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password

OLLAMA_HOST=http://your_ollama_host:11434
```

5. Ensure pgvector is installed and enabled in your PostgreSQL database:

```sql
CREATE EXTENSION vector;
```

6. Pull the embedding model in Ollama:

```bash
ollama pull nomic-embed-text
```

## Usage

### Using the Notebook

The easiest way to get started is with the Jupyter notebook:

```bash
source venv/bin/activate
jupyter notebook notebooks/load_and_search.ipynb
```

The notebook walks you through:
1. Creating the database schema
2. Loading your Logseq documents
3. Generating embeddings (optional, for semantic search)
4. Running different types of searches

### Using the Library

```python
from pathlib import Path
from logseq_searcher import (
    init_db,
    init_ollama,
    create_schema,
    load_logseq_vault,
    add_embeddings_to_existing,
    search,
    semantic_search,
    hybrid_search,
)

# Initialize connections
init_db(Path('.env'))
init_ollama()

# Create schema and load documents
create_schema()
load_logseq_vault(Path.home() / 'path' / 'to' / 'logseq-vault')

# Add embeddings for semantic search
add_embeddings_to_existing(batch_size=50)

# Search!
results = search("Python programming", limit=5)
results = semantic_search("learning techniques", limit=5)
results = hybrid_search("productivity tips", limit=5, fts_weight=0.3, semantic_weight=0.7)
```

## Search Types

### Full-Text Search
```python
search("keyword", limit=10, doc_type='page')  # or 'journal'
```
Traditional keyword matching. Fast and precise.

### Advanced FTS
```python
advanced_search('"exact phrase" OR alternative -excluded', limit=10)
```
Supports quoted phrases, OR, and exclusion.

### Semantic Search
```python
semantic_search("conceptual query", limit=10)
```
Finds documents with similar meaning, even without keyword matches.

### Hybrid Search
```python
hybrid_search("query", limit=10, fts_weight=0.5, semantic_weight=0.5)
```
Combines both approaches. Adjust weights to favor keywords or meaning.

## Development

```bash
source venv/bin/activate
pip install -e .[test]
pytest
```

## License

MIT
