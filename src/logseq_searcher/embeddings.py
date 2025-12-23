"""Embedding generation using Ollama."""

import os
from ollama import Client

# Default model for embeddings
DEFAULT_MODEL = "nomic-embed-text"

_ollama_client = None


def init_ollama(host: str = None):
    """Initialize the Ollama client.

    Args:
        host: Ollama server URL. If None, uses OLLAMA_HOST env var.
    """
    global _ollama_client
    host = host or os.getenv('OLLAMA_HOST')
    if not host:
        raise ValueError("OLLAMA_HOST environment variable not set")
    _ollama_client = Client(host=host)


def get_ollama_client() -> Client:
    """Get the initialized Ollama client.

    Returns:
        The Ollama client.

    Raises:
        RuntimeError: If init_ollama() has not been called.
    """
    if _ollama_client is None:
        raise RuntimeError("Ollama not initialized. Call init_ollama() first.")
    return _ollama_client


def generate_embedding(text: str, model: str = DEFAULT_MODEL) -> list[float]:
    """Generate an embedding for a single text.

    Args:
        text: The text to embed.
        model: The embedding model to use.

    Returns:
        The embedding as a list of floats.
    """
    client = get_ollama_client()
    response = client.embed(model=model, input=text)
    return response['embeddings'][0]


def generate_embeddings(texts: list[str], model: str = DEFAULT_MODEL) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Args:
        texts: List of texts to embed.
        model: The embedding model to use.

    Returns:
        List of embeddings, one per input text.
    """
    client = get_ollama_client()
    response = client.embed(model=model, input=texts)
    return response['embeddings']
