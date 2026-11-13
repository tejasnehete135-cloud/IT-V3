"""Load Campus JSON records and rank them with TF-IDF and keyword overlap."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

VALID_CATEGORIES = {
    "admissions", "fees", "exams", "timetable", "events", "general"
}
STOP_WORDS = {
    "a", "an", "and", "are", "do", "does", "for", "how", "i", "in", "is",
    "me", "of", "on", "please", "tell", "the", "to", "what", "when", "where",
    "which", "who", "with", "my", "can", "much", "many", "about", "at",
}


class KnowledgeRetriever:
    """Index one JSON record per campus fact, FAQ, or policy."""

    def __init__(self, data_dir: Path, top_k: int = 4) -> None:
        self.data_dir = Path(data_dir)
        self.top_k = min(5, max(3, top_k))
        self.records: List[Dict[str, object]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        self.reload()

    def reload(self) -> int:
        if not self.data_dir.is_dir():
            raise FileNotFoundError(f"Campus data directory not found: {self.data_dir}")

        records: List[Dict[str, object]] = []
        for path in sorted(self.data_dir.glob("*.json")):
            with path.open(encoding="utf-8") as data_file:
                document = json.load(data_file)
            if not isinstance(document, list):
                raise ValueError(f"{path.name} must contain a JSON array of records.")
            for record in document:
                if not isinstance(record, dict):
                    raise ValueError(f"{path.name} contains a non-object record.")
                if not all(
                    isinstance(record.get(key), str) and record[key].strip()
                    for key in ("id", "category", "question", "answer")
                ):
                    raise ValueError(
                        f"Every record in {path.name} needs id, category, question, and answer."
                    )
                keywords = record.get("keywords")
                if (
                    not isinstance(keywords, list)
                    or not keywords
                    or not all(isinstance(item, str) for item in keywords)
                ):
                    raise ValueError(f"Every record in {path.name} needs keyword strings.")
                record_category = record["category"].lower()
                if record_category not in VALID_CATEGORIES:
                    raise ValueError(
                        f"Unsupported category {record['category']!r} in {path.name}."
                    )
                records.append({
                    **record,
                    "category": record_category,
                    "keywords": [keyword.lower() for keyword in keywords],
                    "source_file": path.name,
                })

        if not records:
            raise ValueError(f"No Campus records found in {self.data_dir}")

        vectorizer = TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), stop_words=sorted(STOP_WORDS)
        )
        matrix = vectorizer.fit_transform(
            [
                f"{record['category']} {record['question']} "
                f"{' '.join(record['keywords'])} {record['answer']}"
                for record in records
            ]
        )
        self.records = records
        self.vectorizer = vectorizer
        self.matrix = matrix
        return len(records)

    @staticmethod
    def _query_terms(query: str) -> set[str]:
        return {
            term.lower()
            for term in re.findall(r"\b[\w@.+-]+\b", query)
            if len(term) > 1 and term.lower() not in STOP_WORDS
        }

    def _rank(
        self,
        query: str,
        category: Optional[str] = None,
    ) -> List[Tuple[float, Dict[str, object]]]:
        if not self.records or self.vectorizer is None or self.matrix is None:
            return []
        query_vector = self.vectorizer.transform([query])
        tfidf_scores = cosine_similarity(query_vector, self.matrix).ravel()
        query_terms = self._query_terms(query)
        ranked: List[Tuple[float, Dict[str, object]]] = []

        for index, record in enumerate(self.records):
            if category and record["category"] != category.lower():
                continue
            question = str(record["question"]).lower()
            keywords = set(record["keywords"])
            content_terms = self._query_terms(
                f"{question} {' '.join(record['keywords'])} {record['answer']}"
            )
            keyword_hits = query_terms.intersection(keywords)
            content_hits = query_terms.intersection(content_terms)
            coverage = len(content_hits) / max(1, len(query_terms))
            score = (
                float(tfidf_scores[index])
                + len(keyword_hits) * 0.12
                + coverage * 0.25
            )
            if question and question in query.lower():
                score += 0.4
            ranked.append((score, record))
        return sorted(ranked, key=lambda item: (-item[0], str(item[1]["id"])))

    def search(
        self, query: str, top_k: Optional[int] = None, category: Optional[str] = None
    ) -> List[Dict[str, object]]:
        ranked = self._rank(query, category)
        if not ranked:
            return []
        limit = min(5, max(3, top_k or self.top_k))
        terms = self._query_terms(query)
        if not terms:
            return []
        best_score = ranked[0][0]
        if best_score < 0.3:
            return []
        return [
            record.copy()
            for score, record in ranked[:limit]
            if score >= max(0.12, best_score * 0.28)
        ]

    def fallback_answer(self, query: str) -> Optional[Dict[str, object]]:
        """Return the best sufficiently relevant record when LM Studio is down."""
        ranked = self._rank(query)
        if ranked and ranked[0][0] >= 0.42 and self._query_terms(query):
            return ranked[0][1].copy()
        return None

    def helpdesk_contact(self) -> Optional[Dict[str, object]]:
        """Find the designated general Campus Helpdesk contact record."""
        return next(
            (
                record.copy()
                for record in self.records
                if record["category"] == "general"
                and "campus helpdesk" in record["keywords"]
            ),
            None,
        )
