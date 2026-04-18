"""Retrieval-Augmented Generation for grounded conversation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

RAG_DIR = Path.home() / ".memory-mcp" / "rag"
RAG_DIR.mkdir(exist_ok=True, parents=True)


class RetrievalStrategy(Enum):
    """Document retrieval approaches"""
    DENSE = "dense"  # Semantic similarity
    SPARSE = "sparse"  # BM25 keyword matching
    HYBRID = "hybrid"  # Combination
    RERANKED = "reranked"  # With reranking


class GroundingType(Enum):
    """Types of grounding"""
    CITED = "cited"  # Retrieved document cited
    INFERRED = "inferred"  # Implicit in documents
    HYBRID = "hybrid"  # Mix of both
    UNGROUNDED = "ungrounded"  # Not grounded


@dataclass
class RetrievedDocument:
    """Document retrieved for context"""
    doc_id: str
    content: str
    source: str
    relevance_score: float  # 0-1
    rank: int
    snippets: List[str] = field(default_factory=list)  # Key passages

    def to_dict(self) -> Dict:
        """Serialize document"""
        return {
            "doc_id": self.doc_id,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "rank": self.rank,
            "snippet_count": len(self.snippets),
            "content_length": len(self.content),
        }


@dataclass
class Citation:
    """Citation in generated text"""
    doc_id: str
    source: str
    quote: str
    claim: str
    relevance: float

    def to_dict(self) -> Dict:
        """Serialize citation"""
        return {
            "source": self.source,
            "quote": self.quote,
            "claim": self.claim,
            "relevance": self.relevance,
        }


@dataclass
class RAGResponse:
    """Response generated with retrieval-augmented generation"""
    response_id: str
    query: str
    response_text: str
    documents_used: List[RetrievedDocument]
    citations: List[Citation] = field(default_factory=list)
    grounding_type: GroundingType = GroundingType.CITED
    hallucination_risk: float = 0.0  # 0-1, higher = more risk
    confidence: float = 0.8
    coverage: float = 0.0  # % of claims grounded
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize response"""
        return {
            "response_id": self.response_id,
            "query": self.query,
            "response_text": self.response_text,
            "documents_used": len(self.documents_used),
            "citations": len(self.citations),
            "grounding_type": self.grounding_type.value,
            "hallucination_risk": self.hallucination_risk,
            "confidence": self.confidence,
            "coverage": self.coverage,
            "created_at": self.created_at,
        }


class DocumentRetriever:
    """Retrieve relevant documents"""

    def __init__(self):
        self.documents: Dict[str, str] = {}
        self.embeddings: Dict[str, List[float]] = {}

    def index_document(self, doc_id: str, content: str):
        """Index document"""
        self.documents[doc_id] = content
        # Simulated embedding
        self.embeddings[doc_id] = [hash(content) % 100 / 100 for _ in range(128)]

    def retrieve_dense(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Dense retrieval using embeddings"""
        # Simulated similarity
        query_embedding = [hash(query) % 100 / 100 for _ in range(128)]

        scores = []
        for doc_id, doc_embedding in self.embeddings.items():
            # Simple cosine similarity
            similarity = sum(a * b for a, b in zip(query_embedding, doc_embedding)) / (
                sum(a ** 2 for a in query_embedding) ** 0.5 *
                sum(b ** 2 for b in doc_embedding) ** 0.5
            ) if any(query_embedding) and any(doc_embedding) else 0.0
            scores.append((doc_id, similarity))

        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]

    def retrieve_sparse(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Sparse retrieval using keywords"""
        query_words = set(query.lower().split())

        scores = []
        for doc_id, content in self.documents.items():
            doc_words = set(content.lower().split())
            overlap = len(query_words & doc_words)
            score = overlap / len(query_words) if query_words else 0.0
            scores.append((doc_id, score))

        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]

    def retrieve_hybrid(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> List[Tuple[str, float]]:
        """Hybrid retrieval combining dense and sparse"""
        dense_results = {doc_id: score for doc_id, score in self.retrieve_dense(query, top_k * 2)}
        sparse_results = {doc_id: score for doc_id, score in self.retrieve_sparse(query, top_k * 2)}

        combined = {}
        for doc_id in set(list(dense_results.keys()) + list(sparse_results.keys())):
            dense_score = dense_results.get(doc_id, 0.0)
            sparse_score = sparse_results.get(doc_id, 0.0)
            combined[doc_id] = alpha * dense_score + (1 - alpha) * sparse_score

        return sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_k]


class HalluccinationDetector:
    """Detect hallucinations in generated text"""

    @staticmethod
    def detect_unsupported_claims(
        response_text: str,
        documents: List[RetrievedDocument],
    ) -> Tuple[List[str], float]:
        """Identify claims not supported by documents"""
        doc_content = " ".join(d.content for d in documents).lower()

        sentences = response_text.split(".")
        unsupported = []
        risk_score = 0.0

        for sentence in sentences:
            sentence_lower = sentence.lower().strip()

            if not sentence_lower:
                continue

            # Check if key phrases are in documents
            words = sentence_lower.split()
            doc_coverage = sum(1 for w in words if w in doc_content) / len(words) if words else 0.0

            if doc_coverage < 0.3:  # <30% word overlap
                unsupported.append(sentence.strip())
                risk_score += 1.0

        risk_score = min(1.0, risk_score / max(1, len(sentences)))

        return unsupported, risk_score

    @staticmethod
    def extract_claims(text: str) -> List[str]:
        """Extract factual claims from text"""
        # Simple heuristic: sentences with verbs
        sentences = text.split(".")
        claims = [s.strip() for s in sentences if len(s.split()) > 3 and s.strip()]
        return claims


class RAGSystem:
    """Complete RAG system"""

    def __init__(self):
        self.retriever = DocumentRetriever()
        self.detector = HallucinationDetector()
        self.responses: Dict[str, RAGResponse] = {}

    def add_document(self, doc_id: str, content: str, metadata: Optional[Dict] = None):
        """Add document to knowledge base"""
        self.retriever.index_document(doc_id, content)

    def generate_with_retrieval(
        self,
        query: str,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        top_k: int = 5,
        agent_fn: Optional[callable] = None,
    ) -> RAGResponse:
        """Generate response with retrieval"""
        # Retrieve documents
        if strategy == RetrievalStrategy.DENSE:
            retrieved = self.retriever.retrieve_dense(query, top_k)
        elif strategy == RetrievalStrategy.SPARSE:
            retrieved = self.retriever.retrieve_sparse(query, top_k)
        else:  # HYBRID
            retrieved = self.retriever.retrieve_hybrid(query, top_k)

        # Build context
        documents = [
            RetrievedDocument(
                doc_id=doc_id,
                content=self.retriever.documents[doc_id],
                source=f"doc_{doc_id}",
                relevance_score=score,
                rank=i + 1,
            )
            for i, (doc_id, score) in enumerate(retrieved)
        ]

        # Generate response (simulated)
        if agent_fn:
            context = "\n".join([f"[{d.source}] {d.content[:100]}" for d in documents])
            response_text = agent_fn(f"{query}\n\nContext:\n{context}")
        else:
            response_text = f"[Generated response to: {query}]"

        # Detect hallucinations
        unsupported, hallucination_risk = self.detector.detect_unsupported_claims(
            response_text,
            documents,
        )

        # Calculate coverage (% of claims grounded)
        claims = self.detector.extract_claims(response_text)
        coverage = (len(claims) - len(unsupported)) / len(claims) if claims else 0.0

        # Extract citations
        citations = []
        for doc in documents[:3]:  # Top 3 docs
            citations.append(
                Citation(
                    doc_id=doc.doc_id,
                    source=doc.source,
                    quote=doc.content[:50],
                    claim=response_text[:50],
                    relevance=doc.relevance_score,
                )
            )

        response = RAGResponse(
            response_id=f"rag_{len(self.responses)}",
            query=query,
            response_text=response_text,
            documents_used=documents,
            citations=citations,
            hallucination_risk=hallucination_risk,
            coverage=coverage,
        )

        self.responses[response.response_id] = response
        return response

    def get_grounding_report(self, response_id: str) -> Optional[Dict]:
        """Get grounding analysis"""
        if response_id not in self.responses:
            return None

        response = self.responses[response_id]

        return {
            "response_id": response_id,
            "query": response.query,
            "grounding_type": response.grounding_type.value,
            "coverage": response.coverage,
            "hallucination_risk": response.hallucination_risk,
            "documents_used": len(response.documents_used),
            "citations": len(response.citations),
            "health": "good" if response.hallucination_risk < 0.3 else "at_risk",
        }

    def get_rag_statistics(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        total_responses = len(self.responses)
        avg_hallucination_risk = (
            sum(r.hallucination_risk for r in self.responses.values()) / total_responses
            if total_responses > 0
            else 0.0
        )
        avg_coverage = (
            sum(r.coverage for r in self.responses.values()) / total_responses
            if total_responses > 0
            else 0.0
        )

        return {
            "total_responses": total_responses,
            "documents_indexed": len(self.retriever.documents),
            "avg_hallucination_risk": avg_hallucination_risk,
            "avg_coverage": avg_coverage,
            "high_risk_responses": sum(
                1 for r in self.responses.values()
                if r.hallucination_risk > 0.5
            ),
        }


# Global system
rag_system = RAGSystem()


# MCP Tools (add to memory_server.py)

def add_rag_document(doc_id: str, content: str) -> dict:
    """Add document to RAG knowledge base"""
    rag_system.add_document(doc_id, content)
    return {"doc_id": doc_id, "indexed": True}


def generate_with_rag(
    query: str,
    strategy: str = "hybrid",
    top_k: int = 5,
) -> dict:
    """Generate response with retrieval"""
    response = rag_system.generate_with_retrieval(
        query,
        RetrievalStrategy(strategy),
        top_k,
    )
    return response.to_dict()


def get_rag_grounding_report(response_id: str) -> dict:
    """Get grounding analysis"""
    report = rag_system.get_grounding_report(response_id)
    return report or {"error": "Response not found"}


def get_rag_statistics() -> dict:
    """Get RAG statistics"""
    return rag_system.get_rag_statistics()


if __name__ == "__main__":
    # Test RAG
    system = RAGSystem()

    # Add documents
    system.add_document(
        "doc_1",
        "Python is a high-level programming language created by Guido van Rossum.",
    )
    system.add_document(
        "doc_2",
        "Python supports multiple programming paradigms including OOP and functional programming.",
    )

    # Generate with retrieval
    response = system.generate_with_retrieval("What is Python?")
    print(f"Response: {response.response_text}")
    print(f"Hallucination risk: {response.hallucination_risk:.2f}")
    print(f"Coverage: {response.coverage:.2f}")

    # Statistics
    stats = system.get_rag_statistics()
    print(f"Stats: {json.dumps(stats, indent=2)}")
