"""Simple offline knowledge-base retriever built with scikit-learn TF-IDF."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KnowledgeBaseRetriever:
    """Return the top matching documents for a natural-language query."""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        base_dir = Path(root_dir) if root_dir is not None else Path(__file__).resolve().parents[1] / "data" / "knowledge_base"
        self.base_dir = Path(base_dir)
        self.documents: List[Tuple[str, str]] = []
        self.vectorizer = None
        self.matrix = None
        self._load_docs()

    def _load_docs(self) -> None:
        if not self.base_dir.exists():
            self.documents = []
            self.vectorizer = None
            self.matrix = None
            return

        docs: List[Tuple[str, str]] = []
        for path in sorted(self.base_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            docs.append((path.name, text))
        self.documents = docs
        if not docs:
            self.vectorizer = None
            self.matrix = None
            return

        corpus = [text for _, text in docs]
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
        self.matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """Return a list of matching knowledge-base chunks with their source names."""
        if not query or self.vectorizer is None or self.matrix is None or not self.documents:
            return []

        qv = self.vectorizer.transform([query])
        sims = cosine_similarity(qv, self.matrix).ravel()
        ranked = sorted(enumerate(sims), key=lambda item: item[1], reverse=True)[:top_k]

        results: List[Dict[str, str]] = []
        for idx, score in ranked:
            name, text = self.documents[idx]
            if score <= 0:
                continue
            results.append({"source": name, "score": f"{score:.4f}", "text": text[:2000]})
        return results
