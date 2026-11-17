"""
Diagram, Table, and File-Attachment Evaluator.
Handles:
1. Structured table evaluation (state transition tables, tabular answers)
2. PDF text extraction & validation
3. Image upload inspection & routing to teacher review
"""
import os
import json
from typing import Dict, Any, List

def evaluate_diagram_or_file(
    question_text: str,
    reference_answer: str,
    student_answer: str,
    max_marks: float = 1.0,
    rubric: str = None,
    file_reference: str = None,
    structured_answer: str = None
) -> Dict[str, Any]:
    max_marks = float(max_marks)
    
    # 1. Check for Structured Table / Data
    if structured_answer:
        try:
            table_data = json.loads(structured_answer) if isinstance(structured_answer, str) else structured_answer
            if isinstance(table_data, dict) and ("table" in table_data or "rows" in table_data):
                headers = table_data.get("headers", [])
                rows = table_data.get("rows", table_data.get("table", []))
                
                if not rows:
                    return {
                        "suggested_marks": 0.0,
                        "max_marks": max_marks,
                        "explanation": "Structured table was submitted with zero data rows.",
                        "confidence": 1.0,
                        "review_status": "COMPLETED",
                        "evaluation_method": "STRUCTURED_TABLE",
                        "model_name": "table-evaluator-1.0",
                        "issues": ["EMPTY_TABLE"]
                    }
                
                # Check if reference_answer contains a reference table
                ref_table_data = None
                if reference_answer:
                    try:
                        ref_parsed = json.loads(reference_answer) if isinstance(reference_answer, str) else reference_answer
                        if isinstance(ref_parsed, dict) and ("table" in ref_parsed or "rows" in ref_parsed):
                            ref_table_data = ref_parsed
                    except Exception:
                        pass
                
                if ref_table_data:
                    ref_headers = ref_table_data.get("headers", [])
                    ref_rows = ref_table_data.get("rows", ref_table_data.get("table", []))
                    
                    total_cells = max(1, sum(len(r) if isinstance(r, list) else len(r.values()) for r in ref_rows))
                    matched_cells = 0
                    
                    for r_idx, ref_r in enumerate(ref_rows):
                        if r_idx < len(rows):
                            stu_r = rows[r_idx]
                            if isinstance(ref_r, list) and isinstance(stu_r, list):
                                for c_idx, ref_cell in enumerate(ref_r):
                                    if c_idx < len(stu_r) and str(stu_r[c_idx]).strip().lower() == str(ref_cell).strip().lower():
                                        matched_cells += 1
                            elif isinstance(ref_r, dict) and isinstance(stu_r, dict):
                                for k, ref_v in ref_r.items():
                                    if k in stu_r and str(stu_r[k]).strip().lower() == str(ref_v).strip().lower():
                                        matched_cells += 1
                    
                    match_ratio = min(1.0, matched_cells / total_cells)
                    score = round(max_marks * match_ratio, 2)
                    conf = 1.0 if match_ratio >= 0.95 else 0.80
                    status = "COMPLETED" if match_ratio >= 0.95 else "NEEDS_REVIEW"
                    
                    return {
                        "suggested_marks": score,
                        "max_marks": max_marks,
                        "explanation": f"Table cell comparison: {matched_cells}/{total_cells} cells matched reference table ({int(match_ratio*100)}%).",
                        "confidence": conf,
                        "review_status": status,
                        "evaluation_method": "STRUCTURED_TABLE",
                        "model_name": "table-evaluator-1.0",
                        "issues": [] if match_ratio >= 0.95 else ["PARTIAL_TABLE_MATCH"]
                    }
                else:
                    # Baseline structured table evaluation routed for teacher confirmation
                    baseline_marks = round(max_marks * 0.80, 2)
                    return {
                        "suggested_marks": baseline_marks,
                        "max_marks": max_marks,
                        "explanation": f"Structured table received ({len(rows)} rows, {len(headers)} columns). Baseline awarded; routed for teacher verification against reference solution.",
                        "confidence": 0.70,
                        "review_status": "NEEDS_REVIEW",
                        "evaluation_method": "STRUCTURED_TABLE",
                        "model_name": "table-evaluator-1.0",
                        "issues": []
                    }
        except Exception as e:
            print(f"[diagram_evaluator] Table parsing error: {e}")

    # 2. Check for File Upload (PDF / Image)
    if file_reference:
        if not os.path.exists(file_reference):
            return {
                "suggested_marks": 0.0,
                "max_marks": max_marks,
                "explanation": f"Referenced file not found on server: {os.path.basename(file_reference)}.",
                "confidence": 1.0,
                "review_status": "COMPLETED",
                "evaluation_method": "FILE_ATTACHMENT",
                "model_name": "file-inspector",
                "issues": ["FILE_NOT_FOUND"]
            }

        filename = os.path.basename(file_reference).lower()
        file_size_kb = round(os.path.getsize(file_reference) / 1024, 2)
        
        # A. Digital PDF Extraction
        if filename.endswith('.pdf'):
            try:
                import pypdf
                reader = pypdf.PdfReader(file_reference)
                num_pages = len(reader.pages)
                extracted_text = ""
                for p in reader.pages[:5]: # inspect first 5 pages
                    extracted_text += p.extract_text() or ""
                    
                extracted_text = extracted_text.strip()
                if len(extracted_text) > 30:
                    # Successfully extracted digital PDF text! Route through text evaluator
                    from ai.evaluation.text_evaluator import evaluate_text_answer
                    text_result = evaluate_text_answer(
                        question_text=question_text,
                        reference_answer=reference_answer,
                        student_answer=extracted_text,
                        max_marks=max_marks,
                        rubric=rubric
                    )
                    text_result["explanation"] = f"[PDF Extracted ({num_pages} pages)] " + text_result.get("explanation", "")
                    text_result["evaluation_method"] = "PDF_TEXT_EXTRACTION"
                    return text_result
                else:
                    return {
                        "suggested_marks": 0.0,
                        "max_marks": max_marks,
                        "explanation": f"Scanned or handwritten PDF uploaded ({num_pages} pages, {file_size_kb} KB). No digital text layer detected. Requires manual teacher grading.",
                        "confidence": 0.50,
                        "review_status": "NEEDS_REVIEW",
                        "evaluation_method": "FILE_ATTACHMENT",
                        "model_name": "pdf-scanned-inspector",
                        "issues": ["SCANNED_PDF_MANUAL_REVIEW"]
                    }
            except Exception as e:
                return {
                    "suggested_marks": 0.0,
                    "max_marks": max_marks,
                    "explanation": f"PDF inspection error: {str(e)[:80]}. Routed to teacher review.",
                    "confidence": 0.40,
                    "review_status": "NEEDS_REVIEW",
                    "evaluation_method": "FILE_ATTACHMENT",
                    "model_name": "pdf-inspector-fallback",
                    "issues": ["PDF_PARSE_ERROR"]
                }
                
        # B. Image Upload (PNG / JPEG)
        if any(filename.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
            return {
                "suggested_marks": 0.0,
                "max_marks": max_marks,
                "explanation": f"Handwritten diagram/solution image uploaded ({file_size_kb} KB). Visual solution routed directly to teacher grading queue.",
                "confidence": 0.50,
                "review_status": "NEEDS_REVIEW",
                "evaluation_method": "HANDWRITTEN_IMAGE",
                "model_name": "image-attachment-inspector",
                "issues": ["IMAGE_UPLOAD_REQUIRES_TEACHER_REVIEW"]
            }

    # Fallback if neither structured nor file
    return {
        "suggested_marks": 0.0,
        "max_marks": max_marks,
        "explanation": "No diagram, table, or valid file attached.",
        "confidence": 0.90,
        "review_status": "COMPLETED",
        "evaluation_method": "DIAGRAM_EVALUATOR",
        "model_name": "diagram-evaluator",
        "issues": ["NO_DIAGRAM_OR_FILE"]
    }
