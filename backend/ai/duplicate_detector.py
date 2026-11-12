"""
Duplicate Detector using SentenceTransformer (all-MiniLM-L6-v2).

Features:
    - Pairwise duplicate detection for QIS pipeline
    - Batch duplicate grouping for an entire exam
    - Archive workflow for non-primary duplicates

Returns TOP-3 similar questions with risk_label.

Thresholds (MVP heuristics — not calibrated probabilities):
  < 0.70          → LOW
  0.70 – 0.84     → SIMILAR
  >= 0.85         → HIGH_DUPLICATE_RISK

NOTE: 0.91 similarity does NOT mean 91% probability of duplication.
These are cosine similarity scores, not probabilistic estimates.
"""
import json
from datetime import datetime
from typing import List, Dict, Optional

_st_model = None


def _get_st_model():
    global _st_model
    if _st_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _st_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"[duplicate_detector] SentenceTransformer load failed: {e}")
            _st_model = None
    return _st_model


def _get_thresholds():
    return {"HIGH": 0.90, "MEDIUM": 0.80, "LOW": 0.70}

def _risk_label(score: float) -> str:
    th = _get_thresholds()
    if score >= th["HIGH"]:
        return "HIGH_DUPLICATE_RISK"
    elif score >= th["MEDIUM"]:
        return "MEDIUM_DUPLICATE_RISK"
    elif score >= th["LOW"]:
        return "LOW_DUPLICATE_RISK"
    return "NONE"


def detect_duplicates(new_text: str, existing_questions: List[Dict]) -> dict:
    """
    Compute semantic similarity between new_text and existing_questions.

    Args:
        new_text: Plain-text of the new question.
        existing_questions: list of {"id": int, "text": str}

    Returns: Canonical DuplicateResult dict.
    """
    if not existing_questions or not new_text.strip():
        return _no_duplicate()

    from database import get_db
    db = next(get_db())

    model = _get_st_model()

    if model:
        try:
            from models import QuestionEmbedding
            import numpy as np
            import torch

            q_ids = [q["id"] for q in existing_questions]

            # Batch fetch existing embeddings
            existing_emb_records = db.query(QuestionEmbedding).filter(
                QuestionEmbedding.question_id.in_(q_ids),
                QuestionEmbedding.embedding_model == "all-MiniLM-L6-v2"
            ).all()
            emb_dict = {r.question_id: json.loads(r.embedding_data) for r in existing_emb_records}

            embeddings2_list = []
            valid_qs = []
            new_embeddings_to_save = []

            for q in existing_questions:
                if q["id"] in emb_dict:
                    embeddings2_list.append(emb_dict[q["id"]])
                else:
                    # Compute missing embedding
                    emb = model.encode(q["text"])
                    emb_list = emb.tolist()
                    new_embeddings_to_save.append(QuestionEmbedding(
                        question_id=q["id"],
                        embedding_data=json.dumps(emb_list),
                        embedding_model="all-MiniLM-L6-v2"
                    ))
                    embeddings2_list.append(emb_list)
                valid_qs.append(q)

            # Batch commit new embeddings (fix: was committing per-question)
            if new_embeddings_to_save:
                try:
                    for rec in new_embeddings_to_save:
                        db.add(rec)
                    db.commit()
                except Exception:
                    db.rollback()

            if not valid_qs:
                return _no_duplicate()

            emb1 = model.encode(new_text, convert_to_tensor=True)
            emb2 = torch.tensor(embeddings2_list)

            from sentence_transformers import util
            scores = util.cos_sim(emb1, emb2)[0].tolist()

            # Sort descending
            scored = sorted(zip(scores, valid_qs), key=lambda x: x[0], reverse=True)

            top1_score, top1_q = scored[0]
            top3 = [
                {
                    "question_id": q["id"],
                    "similarity": round(float(s), 4),
                    "text_preview": q["text"][:100]
                }
                for s, q in scored[:3]
                if s >= 0.50  # Only include meaningful similarities
            ]

            th = _get_thresholds()
            return {
                "risk": round(float(top1_score), 4),
                "risk_label": _risk_label(float(top1_score)),
                "is_duplicate": float(top1_score) >= th["MEDIUM"],
                "similar_question_id": top1_q["id"],
                "similarity": round(float(top1_score), 4),
                "similar_questions": top3,
                "method": "sentence_transformer"
            }

        except Exception as e:
            print(f"[duplicate_detector] SentenceTransformer error: {e}")
            # Fall through to difflib

    # Fallback: difflib SequenceMatcher
    return _difflib_fallback(new_text, existing_questions)


def _difflib_fallback(new_text: str, existing_questions: List[Dict]) -> dict:
    import difflib
    scored = []
    for q in existing_questions:
        score = difflib.SequenceMatcher(None, new_text.lower(), q["text"].lower()).ratio()
        scored.append((score, q))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return _no_duplicate()

    top1_score, top1_q = scored[0]
    top3 = [
        {"question_id": q["id"], "similarity": round(float(s), 4), "text_preview": q["text"][:100]}
        for s, q in scored[:3] if s >= 0.40
    ]

    th = _get_thresholds()
    return {
        "risk": round(top1_score, 4),
        "risk_label": _risk_label(top1_score),
        "is_duplicate": top1_score >= th["MEDIUM"],
        "similar_question_id": top1_q["id"],
        "similarity": round(top1_score, 4),
        "similar_questions": top3,
        "method": "difflib_fallback"
    }


def _no_duplicate() -> dict:
    return {
        "risk": 0.0, "risk_label": "LOW", "is_duplicate": False,
        "similar_question_id": None, "similarity": 0.0,
        "similar_questions": [], "method": "none"
    }


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: DUPLICATE GROUPING & ARCHIVAL
# ═══════════════════════════════════════════════════════════════════════════

def group_duplicates(exam_id: int, threshold: float = 0.85) -> dict:
    """
    Scan all questions in an exam, compute pairwise similarity,
    and create DuplicateGroup + QuestionDuplicate records.

    Returns summary: {groups_created, total_flagged, questions_scanned}
    """
    from models import Question, QuestionEmbedding, DuplicateGroup, QuestionDuplicate
    from database import get_db
    db = next(get_db())

    model = _get_st_model()
    if not model:
        return {"error": "SentenceTransformer model not available", "groups_created": 0}

    # Fetch non-archived questions
    questions = db.query(Question).filter_by(exam_id=exam_id).all()
    # Filter out archived manually if needed, or assume all are non-archived if column is absent.
    if len(questions) < 2:
        return {"groups_created": 0, "total_flagged": 0, "questions_scanned": len(questions)}

    # Get or compute embeddings
    q_data = []
    embeddings_list = []

    for q in questions:
        existing_emb = db.query(QuestionEmbedding).filter_by(
            question_id=q.id, embedding_model="all-MiniLM-L6-v2"
        ).first()

        if existing_emb:
            emb = json.loads(existing_emb.embedding_json)
        else:
            emb = model.encode(q.text).tolist()
            db.add(QuestionEmbedding(
                question_id=q.id,
                embedding_data=json.dumps(emb),
                embedding_model="all-MiniLM-L6-v2"
            ))

        q_data.append(q)
        embeddings_list.append(emb)

    db.commit()

    # Pairwise similarity
    import torch
    from sentence_transformers import util

    emb_tensor = torch.tensor(embeddings_list)
    sim_matrix = util.cos_sim(emb_tensor, emb_tensor)

    # Find groups using Union-Find
    n = len(q_data)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if float(sim_matrix[i][j]) >= threshold:
                union(i, j)

    # Build groups
    from collections import defaultdict
    groups = defaultdict(list)
    for i in range(n):
        root = find(i)
        groups[root].append(i)

    # Only keep groups with 2+ members
    dup_groups = {k: v for k, v in groups.items() if len(v) >= 2}

    # Clear old groups for this exam
    old_groups = db.query(DuplicateGroup).filter_by(exam_id=exam_id, status='PENDING').all()
    for og in old_groups:
        db.query(QuestionDuplicate).filter_by(group_id=og.id).delete()
        db.delete(og)
    db.commit()

    # Create new groups
    groups_created = 0
    total_flagged = 0

    for root_idx, member_indices in dup_groups.items():
        group = DuplicateGroup(
            exam_id=exam_id,
            status='PENDING',
            similarity_threshold=threshold
        )
        db.add(group)
        db.flush()  # Get group.id

        # The oldest question (lowest id) is primary
        member_questions = [q_data[i] for i in member_indices]
        member_questions.sort(key=lambda q: q.id)
        primary_q = member_questions[0]

        for mq in member_questions:
            # Compute similarity to primary
            mi = q_data.index(mq)
            pi = q_data.index(primary_q)
            sim_score = float(sim_matrix[mi][pi]) if mi != pi else 1.0

            dup_record = QuestionDuplicate(
                group_id=group.id,
                question_id=mq.id,
                similarity_score=round(sim_score, 4),
                is_primary=(mq.id == primary_q.id),
                status='KEPT' if mq.id == primary_q.id else 'FLAGGED'
            )
            db.add(dup_record)
            total_flagged += 1

        groups_created += 1

    db.commit()

    return {
        "groups_created": groups_created,
        "total_flagged": total_flagged,
        "questions_scanned": len(questions)
    }


def archive_duplicates(group_id: int, keeper_question_id: int = None) -> dict:
    """
    Archive non-primary questions in a duplicate group.
    Sets is_archived=True on Question and status='ARCHIVED' on QuestionDuplicate.

    Args:
        group_id: The DuplicateGroup.id
        keeper_question_id: Optional — override which question to keep.
                           If None, keeps the one marked is_primary.
    """
    from models import Question, DuplicateGroup, QuestionDuplicate
    from database import get_db
    db = next(get_db())

    group = db.get(DuplicateGroup, group_id)
    if not group:
        return {"error": "Group not found"}

    members = db.query(QuestionDuplicate).filter_by(group_id=group_id).all()
    if not members:
        return {"error": "No members in group"}

    # Determine keeper
    if keeper_question_id:
        keeper_ids = {keeper_question_id}
    else:
        keeper_ids = {m.question_id for m in members if m.is_primary}

    if not keeper_ids:
        # Default: keep the oldest (lowest id)
        keeper_ids = {min(m.question_id for m in members)}

    archived_count = 0
    for member in members:
        if member.question_id in keeper_ids:
            member.status = 'KEPT'
            member.is_primary = True
        else:
            member.status = 'ARCHIVED'
            q = db.get(Question, member.question_id)
            if q:
                q.is_archived = True
                archived_count += 1

    group.status = 'RESOLVED'
    group.resolved_at = datetime.utcnow()
    db.commit()

    return {"archived": archived_count, "kept": len(keeper_ids), "group_status": "RESOLVED"}
