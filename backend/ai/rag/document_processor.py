import re

def process_document_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Naively chunks text into overlapping segments of approximately chunk_size characters.
    """
    if not text:
        return []
        
    text = re.sub(r'\s+', ' ', text).strip()
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        if end >= text_length:
            chunks.append(text[start:])
            break
            
        search_window = text[max(start, end - 100):end]
        last_period = search_window.rfind('.')
        
        if last_period != -1:
            end = max(start, end - 100) + last_period + 1
            
        chunks.append(text[start:end].strip())
        
        # Ensure start always advances
        new_start = end - overlap
        if new_start <= start:
            new_start = start + 1
            
        start = new_start
        
    return chunks
