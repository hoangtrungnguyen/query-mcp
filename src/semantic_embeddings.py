"""Semantic embeddings and vector similarity search"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, List
from memory_server import episodic, semantic

# Try to use sentence-transformers (optional)
try:
    from sentence_transformers import SentenceTransformer, util
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False

# Try to use FAISS (optional)
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

EMBEDDINGS_DIR = Path.home() / ".memory-mcp" / "embeddings"
EMBEDDINGS_DIR.mkdir(exist_ok=True, parents=True)


class SemanticEmbedder:
    """Generate and manage semantic embeddings for conversations"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.embeddings_cache = {}
        self.embedding_dim = 384  # Default for MiniLM

        if SBERT_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
            except Exception as e:
                print(f"Failed to load model {model_name}: {e}")

    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for a single text"""
        if not self.model:
            return None

        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.astype(np.float32)
        except Exception as e:
            print(f"Embedding error: {e}")
            return None

    def embed_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """Generate embeddings for multiple texts"""
        if not self.model:
            return None

        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            return embeddings.astype(np.float32)
        except Exception as e:
            print(f"Batch embedding error: {e}")
            return None

    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings"""
        if embedding1 is None or embedding2 is None:
            return 0.0

        if SBERT_AVAILABLE:
            return float(util.pytorch_cos_sim(embedding1, embedding2)[0][0])

        # Fallback: manual cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def save_embedding(self, text_id: str, embedding: np.ndarray):
        """Save embedding to disk"""
        filepath = EMBEDDINGS_DIR / f"{text_id}.npy"
        np.save(filepath, embedding)

    def load_embedding(self, text_id: str) -> Optional[np.ndarray]:
        """Load embedding from disk"""
        filepath = EMBEDDINGS_DIR / f"{text_id}.npy"
        if filepath.exists():
            return np.load(filepath)
        return None


class VectorIndex:
    """FAISS-based vector index for similarity search"""

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.index = None
        self.id_map = {}  # Map FAISS index to message ID
        self.embeddings = []

        if FAISS_AVAILABLE:
            self._init_faiss()

    def _init_faiss(self):
        """Initialize FAISS index"""
        try:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
        except Exception as e:
            print(f"FAISS init error: {e}")
            self.index = None

    def add_embedding(self, text_id: str, embedding: np.ndarray):
        """Add embedding to index"""
        if embedding is None:
            return

        self.id_map[len(self.embeddings)] = text_id
        self.embeddings.append(embedding)

        if FAISS_AVAILABLE and self.index:
            try:
                self.index.add(np.array([embedding]))
            except Exception as e:
                print(f"FAISS add error: {e}")

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[dict]:
        """Find k nearest neighbors"""
        if not query_embedding is not None or len(self.embeddings) == 0:
            return []

        if FAISS_AVAILABLE and self.index:
            try:
                distances, indices = self.index.search(
                    np.array([query_embedding]), k
                )
                results = []
                for idx, distance in zip(indices[0], distances[0]):
                    if idx in self.id_map:
                        results.append(
                            {
                                "text_id": self.id_map[idx],
                                "distance": float(distance),
                                "similarity": 1.0 / (1.0 + float(distance)),
                            }
                        )
                return results
            except Exception as e:
                print(f"FAISS search error: {e}")

        # Fallback: brute force search
        results = []
        for idx, embedding in enumerate(self.embeddings):
            if idx in self.id_map:
                # Use L2 distance
                distance = float(np.linalg.norm(query_embedding - embedding))
                results.append(
                    {
                        "text_id": self.id_map[idx],
                        "distance": distance,
                        "similarity": 1.0 / (1.0 + distance),
                    }
                )

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]

    def build_from_messages(self, messages: List[dict], embedder: SemanticEmbedder):
        """Build index from conversation messages"""
        contents = [m.get("content", "") for m in messages]
        embeddings = embedder.embed_batch(contents)

        if embeddings is None:
            return

        for msg, embedding in zip(messages, embeddings):
            self.add_embedding(msg.get("id"), embedding)


class SemanticClusterer:
    """Cluster messages by semantic similarity"""

    def __init__(self, embedder: SemanticEmbedder):
        self.embedder = embedder

    def cluster_messages(
        self,
        messages: List[dict],
        min_similarity: float = 0.7,
    ) -> List[List[dict]]:
        """
        Cluster messages by semantic similarity.
        Simple agglomerative clustering using threshold.
        """
        if not messages:
            return []

        clusters = []

        for message in messages:
            embedding = self.embedder.embed_text(message.get("content", ""))
            if embedding is None:
                continue

            assigned = False
            for cluster in clusters:
                cluster_embedding = self.embedder.embed_text(
                    cluster[0].get("content", "")
                )
                if cluster_embedding is not None:
                    similarity = self.embedder.cosine_similarity(
                        embedding, cluster_embedding
                    )
                    if similarity >= min_similarity:
                        cluster.append(message)
                        assigned = True
                        break

            if not assigned:
                clusters.append([message])

        return clusters

    def extract_themes(self, clusters: List[List[dict]]) -> List[dict]:
        """Extract themes from clusters"""
        themes = []

        for i, cluster in enumerate(clusters):
            if not cluster:
                continue

            # Simple theme extraction: get the longest message as representative
            representative = max(cluster, key=lambda m: len(m.get("content", "")))
            themes.append(
                {
                    "cluster_id": i,
                    "size": len(cluster),
                    "representative_text": representative.get("content", "")[:100],
                    "member_ids": [m.get("id") for m in cluster],
                }
            )

        return themes


# Global instances
embedder = SemanticEmbedder()
vector_index = VectorIndex()


# MCP Tools (add to memory_server.py)

def semantic_search(agent_id: str, query: str, k: int = 5) -> list:
    """Find semantically similar messages"""
    query_embedding = embedder.embed_text(query)
    if query_embedding is None:
        return []

    results = vector_index.search(query_embedding, k)

    # Enrich with message content
    messages = episodic.get_messages(agent_id, limit=1000)
    msg_dict = {m.get("id"): m for m in messages}

    enriched = []
    for result in results:
        msg = msg_dict.get(result["text_id"])
        if msg:
            enriched.append(
                {
                    "id": result["text_id"],
                    "content": msg.get("content"),
                    "similarity": result["similarity"],
                }
            )

    return enriched


def cluster_conversations(agent_id: str, min_similarity: float = 0.7) -> list:
    """Cluster conversation messages by semantic similarity"""
    messages = episodic.get_messages(agent_id, limit=100)
    clusterer = SemanticClusterer(embedder)
    clusters = clusterer.cluster_messages(messages, min_similarity)
    return clusterer.extract_themes(clusters)


def build_semantic_index(agent_id: str) -> dict:
    """Build vector index from all agent messages"""
    messages = episodic.get_messages(agent_id, limit=1000)
    vector_index.build_from_messages(messages, embedder)
    return {"status": "ok", "indexed_messages": len(messages)}


if __name__ == "__main__":
    # Test embeddings
    if SBERT_AVAILABLE:
        texts = [
            "The quick brown fox jumps over the lazy dog",
            "A fast brown fox leaps over a lazy dog",
            "The weather is nice today",
        ]

        embeddings = embedder.embed_batch(texts)
        print(f"Generated {len(embeddings)} embeddings")
        print(f"Embedding dimension: {embeddings[0].shape}")

        sim = embedder.cosine_similarity(embeddings[0], embeddings[1])
        print(f"Similarity between first two: {sim:.3f}")
    else:
        print("sentence-transformers not available")
