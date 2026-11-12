"""
AI RAG Subsystem: Syllabus Document Processing, Chunk Embedding & Semantic Retrieval.
"""
from .document_processor import process_document_text
from .vector_store import store_document_chunks
from .retriever import retrieve_context

# Alias for compatibility
extract_and_chunk = process_document_text

__all__ = [
    "process_document_text",
    "extract_and_chunk",
    "store_document_chunks",
    "retrieve_context",
]
