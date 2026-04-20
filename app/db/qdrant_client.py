from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import get_settings

settings = get_settings()

_client: QdrantClient | None = None


def get_qdrant() -> QdrantClient:
    """Return a singleton Qdrant client."""
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
    return _client


def ensure_collection(collection_name: str, vector_size: int = 3072) -> None:
    """
    Create the Qdrant collection if it doesn't exist.
    If it exists with a DIFFERENT vector size, delete and recreate it.
    """
    client = get_qdrant()
    existing = {c.name for c in client.get_collections().collections}

    if collection_name in existing:
        # Check actual stored dimension
        info = client.get_collection(collection_name)
        actual_size = info.config.params.vectors.size
        if actual_size == vector_size:
            return  # Already correct — nothing to do
        # Wrong dimension → delete and recreate
        print(f"  ♻️  '{collection_name}' has dim={actual_size}, need {vector_size} → recreating...")
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def ensure_all_collections(vector_size: int = 3072) -> None:
    """Create all disease-specific collections from settings."""
    for name in [
        settings.qdrant_diabetes_collection,
        settings.qdrant_bp_collection,
        settings.qdrant_glands_collection,
    ]:
        ensure_collection(name, vector_size)

