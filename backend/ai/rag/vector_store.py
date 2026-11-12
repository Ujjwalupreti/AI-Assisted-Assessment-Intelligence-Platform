import json
from models import DocumentChunk
from database import SessionLocal
from ai.duplicate_detector import _get_st_model

def store_document_chunks(document_id: int, chunks: list[str]):
    """
    Encodes chunks and saves them to the vector store (DocumentChunk table).
    """
    model = _get_st_model()
    if not model:
        raise RuntimeError("SentenceTransformer model could not be loaded.")
        
    # Generate embeddings in batch
    embeddings = model.encode(chunks)
    
    db = SessionLocal()
    try:
        # Store in database
        for i, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            doc_chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=i,
                chunk_text=chunk_text,
                embedding_json=json.dumps(emb.tolist()),
                model_name="all-MiniLM-L6-v2"
            )
            db.add(doc_chunk)
            
        db.commit()
    finally:
        db.close()
