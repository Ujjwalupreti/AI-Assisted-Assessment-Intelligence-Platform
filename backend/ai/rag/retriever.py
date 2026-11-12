import json
from database import get_db
import torch
from sentence_transformers import util
from models import DocumentChunk
from ai.duplicate_detector import _get_st_model

def retrieve_context(query: str, top_k: int = 3, course_name: str = None) -> str:
    """
    Retrieves the most relevant chunks for a given query using cosine similarity.
    Returns a concatenated string of context.
    """
    db = next(get_db())
    model = _get_st_model()
    if not model or not query.strip():
        return ""
        
    # Fetch all chunks (in a real system you'd use pgvector or FAISS, but for MVP we do in-memory)
    # We could filter by course_name if we joined CourseDocument, but let's keep it simple for MVP.
    all_chunks = db.query(DocumentChunk).all()
    if not all_chunks:
        return ""
        
    chunk_texts = [c.chunk_text for c in all_chunks]
    embeddings_list = [json.loads(c.embedding_json) for c in all_chunks]
    
    query_emb = model.encode(query, convert_to_tensor=True)
    db_embs = torch.tensor(embeddings_list)
    
    scores = util.cos_sim(query_emb, db_embs)[0].tolist()
    
    scored = sorted(zip(scores, chunk_texts), key=lambda x: x[0], reverse=True)
    
    # Filter by a reasonable similarity threshold (e.g. 0.3)
    relevant_chunks = []
    print(f"[RAG Retriever] Top chunks for query '{query}':")
    for score, text in scored[:top_k]:
        if score >= 0.3:
            relevant_chunks.append(text)
            print(f"  - Score: {score:.4f} (Selected)")
        else:
            print(f"  - Score: {score:.4f} (Discarded, < 0.3)")
            
    print(f"[RAG Retriever] Total relevant chunks retrieved: {len(relevant_chunks)}")
    
    if not relevant_chunks:
        return ""
        
    return "\n\n---\n\n".join(relevant_chunks)
