import os

# Safe fallback if sentence_transformers isn't fully installed or crashes
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        if SentenceTransformer is not None:
            print("🚀 Loading SentenceTransformer (all-MiniLM-L6-v2) singleton...")
            # Use a smaller model to save RAM
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            print("⚠️ SentenceTransformer not available. Embeddings will be mocked.")
            self._model = None

    def get_embedding(self, text: str) -> list[float]:
        if not text:
            return []
        if self._model:
            # Output is a numpy array, convert to list of floats
            return self._model.encode(text).tolist()
        else:
            # Mock fallback if library is missing
            return [0.0] * 384

    def get_model(self):
        return self._model

# Create a singleton instance to be imported by other files
embedding_service = EmbeddingService()

def get_embedding(text: str) -> list[float]:
    """Helper function to get embedding for a text."""
    return embedding_service.get_embedding(text)
