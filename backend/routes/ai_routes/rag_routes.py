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
    import json
    res = []
    for d in docs:
        topics = []
        if d.extracted_topics:
            try:
                topics = json.loads(d.extracted_topics)
            except:
                pass
        res.append({
            "id": d.id,
            "title": d.title,
            "course_name": d.course_name,
            "extracted_topics": topics,
            "created_at": d.created_at.isoformat()
        })
    return res

@rag_bp.post('/documents', status_code=201)
def upload_document(data: dict = Body(...), db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    """Upload a new document, chunk it, and generate embeddings."""
    try:
        title = data.get('title')
        content_text = data.get('content_text')
        course_name = data.get('course_name')
        
        if not title or not content_text:
            raise HTTPException(status_code=400, detail="Title and content_text are required.")
            
        extracted_topics = []
        try:
            from ai.rag.document_processor import extract_topics_from_text
            from models import Question
            existing_topics_query = db.query(Question.topic).filter(Question.topic != None).distinct().all()
            existing_topics = [row[0] for row in existing_topics_query if row[0]]
            
            extracted_topics = extract_topics_from_text(content_text, existing_topics=existing_topics)
        except Exception as e:
            print("Failed to extract topics:", e)

        import json
        doc = CourseDocument(
            title=title,
            content_text=content_text,
            course_name=course_name,
            extracted_topics=json.dumps(extracted_topics),
            created_by=teacher.id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Process chunks
        chunks = process_document_text(content_text)
        if chunks:
            store_document_chunks(doc.id, chunks) # note: store_document_chunks needs to be checked if it uses db.session
            
        return {"message": "Document uploaded and processed successfully.", "id": doc.id, "chunks": len(chunks), "extracted_topics": extracted_topics}
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

@rag_bp.post('/analyze-syllabus')
def analyze_syllabus_route(data: dict = Body(...), db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    """Analyze a syllabus document and return structured topics and subtopics."""
    try:
        document_id = data.get("document_id")
        content = data.get("content")
        
        if document_id:
            doc = db.query(CourseDocument).filter(CourseDocument.id == document_id).first()
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found.")
            content = doc.content_text
            
        if not content:
            raise HTTPException(status_code=400, detail="Document ID or content is required.")
            
        from ai.rag.syllabus_analyzer import analyze_syllabus
        result = analyze_syllabus(content)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
