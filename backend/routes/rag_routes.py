from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models import CourseDocument, DocumentChunk, User
from database import get_db
from auth_middleware import get_teacher_user
from ai.rag.document_processor import process_document_text
from ai.rag.vector_store import store_document_chunks

rag_bp = APIRouter()

@rag_bp.get('/documents')
def list_documents(db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    """List all course documents."""
    docs = db.query(CourseDocument).all()
    return [{
        "id": d.id,
        "title": d.title,
        "course_name": d.course_name,
        "created_at": d.created_at.isoformat()
    } for d in docs]

@rag_bp.post('/documents', status_code=201)
def upload_document(data: dict = Body(...), db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    """Upload a new document, chunk it, and generate embeddings."""
    try:
        title = data.get('title')
        content_text = data.get('content_text') or data.get('content')
        course_name = data.get('course_name')
        
        if not title or not content_text:
            raise HTTPException(status_code=400, detail="Title and content_text are required.")
            
        doc = CourseDocument(
            title=title,
            content_text=content_text,
            course_name=course_name,
            created_by=teacher.id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Process chunks
        chunks = process_document_text(content_text)
        if chunks:
            store_document_chunks(doc.id, chunks) # note: store_document_chunks needs to be checked if it uses db.session
            
        return {"message": "Document uploaded and processed successfully.", "id": doc.id, "chunks": len(chunks)}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@rag_bp.delete('/documents/{doc_id}')
def delete_document(doc_id: int, db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    """Delete a document and its chunks (handled via CASCADE in DB if configured, else manual)."""
    try:
        doc = db.get(CourseDocument, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Not found")
            
        # Manually delete chunks if CASCADE is not working on sqlite
        db.query(DocumentChunk).filter_by(document_id=doc.id).delete()
        db.delete(doc)
        db.commit()
        return {"message": "Deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
