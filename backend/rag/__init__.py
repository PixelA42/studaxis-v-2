"""RAG utilities for topic-aware retrieval and extraction."""

from .topic_extractor import extract_dominant_topics, map_question_to_topics

__all__ = ["extract_dominant_topics", "map_question_to_topics"]
