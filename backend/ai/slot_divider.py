"""
Exam Slot Divider.

Generates balanced exam slots (question paper variants) from a question pool.

Algorithm:
1. Collect eligible questions (non-archived, analyzed)
2. Group by topic/bloom/difficulty
3. Greedy allocation: distribute questions across slots ensuring:
   - Each slot has the required number of questions
   - Blueprint distributions are matched as closely as possible
   - No question appears in multiple slots
   - High-quality questions are preferred
4. Rebalance: swap questions between slots to minimize distribution error

Output: List of slots, each with questions and per-slot metrics.
"""
import json
import random
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from models import Question, ExamSlot, ExamSlotQuestion
from database import get_db

def generate_slots(
    exam_id: int,
    num_slots: int = 2,
    questions_per_slot: int = None,
    blueprint: dict = None,
    seed: int = None
) -> dict:
    """
    Generate balanced exam slots.
    
    Args:
        exam_id: The exam to generate slots for.
        num_slots: Number of slots (paper variants) to generate.
        questions_per_slot: Questions per slot. If None, divides evenly.
        blueprint: Optional blueprint for distribution targets.
        seed: Random seed for reproducibility.
        
    Returns:
    {
        "exam_id": int,
        "num_slots": int,
        "slots": [
            {
                "slot_number": int,
                "question_ids": [int],
                "question_count": int,
                "total_marks": float,
                "bloom_distribution": {},
                "difficulty_distribution": {},
                "topic_distribution": {},
                "quality_score": float,
                "blueprint_match_score": float
            }
        ],
        "unassigned_questions": [int],
        "overall_quality": float
    }
    """
    if seed is not None:
        random.seed(seed)

    from database import get_db
    db = next(get_db())

    # Fetch eligible questions
    questions = db.query(Question).filter_by(
        exam_id=exam_id, is_archived=False
    ).all()

    if not questions:
        return {"error": "No questions available.", "slots": []}

    total_q = len(questions)

    if questions_per_slot is None:
        questions_per_slot = total_q // num_slots

    if total_q < num_slots:
        return {"error": f"Not enough questions ({total_q}) for {num_slots} slots.", "slots": []}

    needed = num_slots * questions_per_slot
    if needed > total_q:
        # Reduce questions_per_slot to fit
        questions_per_slot = total_q // num_slots
        needed = num_slots * questions_per_slot

    # Sort questions by quality (best first), then shuffle within quality tiers
    questions_sorted = sorted(
        questions,
        key=lambda q: -(q.ai_quality_score or 0.5)
    )

    # ─── Strategy: Stratified Allocation ──────────────────────────────────
    # Group questions by (topic, bloom_level, difficulty) for balanced allocation
    strata = defaultdict(list)
    for q in questions_sorted:
        key = (q.topic or "General", q.bloom_level or "Remember", q.difficulty or "Medium")
        strata[key].append(q)

    # Initialize slots
    slots: List[List[Question]] = [[] for _ in range(num_slots)]
    used_ids = set()

    # Round-robin allocation from each stratum
    for stratum_key, stratum_qs in strata.items():
        random.shuffle(stratum_qs)
        for i, q in enumerate(stratum_qs):
            if q.id in used_ids:
                continue
            # Find the slot with fewest questions
            target_slot = min(range(num_slots), key=lambda s: len(slots[s]))
            if len(slots[target_slot]) < questions_per_slot:
                slots[target_slot].append(q)
                used_ids.add(q.id)

    # Fill any remaining capacity
    remaining = [q for q in questions_sorted if q.id not in used_ids]
    for q in remaining:
        target_slot = min(range(num_slots), key=lambda s: len(slots[s]))
        if len(slots[target_slot]) < questions_per_slot:
            slots[target_slot].append(q)
            used_ids.add(q.id)

    # ─── Rebalance: Minimize distribution error ──────────────────────────
    if blueprint:
        _rebalance_slots(slots, blueprint, max_iterations=50)

    # ─── Build output ─────────────────────────────────────────────────────
    slot_results = []
    total_quality = 0.0

    for i, slot_qs in enumerate(slots):
        bloom_dist = {}
        diff_dist = {}
        topic_dist = {}
        total_marks = 0.0
        quality_sum = 0.0

        for q in slot_qs:
            bloom = q.bloom_level or "Uncategorized"
            diff = q.difficulty or "Uncategorized"
            topic = q.topic or "Uncategorized"
            bloom_dist[bloom] = bloom_dist.get(bloom, 0) + 1
            diff_dist[diff] = diff_dist.get(diff, 0) + 1
            topic_dist[topic] = topic_dist.get(topic, 0) + 1
            total_marks += (q.max_marks or 1.0)
            quality_sum += (q.ai_quality_score or 0.5)

        avg_quality = quality_sum / len(slot_qs) if slot_qs else 0
        total_quality += avg_quality

        bp_match = _calculate_blueprint_match(bloom_dist, diff_dist, topic_dist, len(slot_qs), blueprint) if blueprint else None

        slot_results.append({
            "slot_number": i + 1,
            "question_ids": [q.id for q in slot_qs],
            "question_count": len(slot_qs),
            "total_marks": round(total_marks, 1),
            "bloom_distribution": bloom_dist,
            "difficulty_distribution": diff_dist,
            "topic_distribution": topic_dist,
            "quality_score": round(avg_quality, 3),
            "blueprint_match_score": round(bp_match, 3) if bp_match is not None else None
        })

    unassigned = [q.id for q in questions if q.id not in used_ids]
    overall_quality = total_quality / num_slots if num_slots > 0 else 0

    return {
        "exam_id": exam_id,
        "num_slots": num_slots,
        "questions_per_slot": questions_per_slot,
        "slots": slot_results,
        "unassigned_questions": unassigned,
        "overall_quality": round(overall_quality, 3)
    }


def save_slots(exam_id: int, slot_data: dict) -> dict:
    """
    Persist generated slots to the database.
    Clears old slots for this exam first.
    """
    from database import get_db
    db = next(get_db())
    
    # Clear old slots
    old_slots = db.query(ExamSlot).filter_by(exam_id=exam_id).all()
    for old in old_slots:
        db.query(ExamSlotQuestion).filter_by(slot_id=old.id).delete()
        db.delete(old)
    db.commit()

    saved_slots = []
    for slot_info in slot_data.get("slots", []):
        slot = ExamSlot(
            exam_id=exam_id,
            slot_number=slot_info['slot_number'],
            total_marks=slot_info.get("total_marks", 0.0),
            quality_score=slot_info.get("quality_score"),
            bloom_distribution=json.dumps(slot_info.get("bloom_distribution", {})),
            difficulty_distribution=json.dumps(slot_info.get("difficulty_distribution", {})),
            topic_distribution=json.dumps(slot_info.get("topic_distribution", {}))
        )
        db.add(slot)
        db.flush()

        for order, q_id in enumerate(slot_info.get("question_ids", [])):
            sq = ExamSlotQuestion(slot_id=slot.id, question_id=q_id)
            db.add(sq)

        saved_slots.append(slot.id)

    db.commit()
    return {"saved_slot_ids": saved_slots}


def _rebalance_slots(slots: List[List[Question]], blueprint: dict, max_iterations: int = 50):
    """
    Attempt to swap questions between slots to reduce distribution error.
    Greedy hill-climbing: only accept swaps that improve total error.
    """
    for _ in range(max_iterations):
        improved = False
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                # Try swapping one question from slot i with one from slot j
                for qi_idx in range(len(slots[i])):
                    for qj_idx in range(len(slots[j])):
                        # Calculate error before swap
                        error_before = _slot_error(slots[i], blueprint) + _slot_error(slots[j], blueprint)

                        # Swap
                        slots[i][qi_idx], slots[j][qj_idx] = slots[j][qj_idx], slots[i][qi_idx]

                        # Calculate error after swap
                        error_after = _slot_error(slots[i], blueprint) + _slot_error(slots[j], blueprint)

                        if error_after < error_before:
                            improved = True
                        else:
                            # Revert swap
                            slots[i][qi_idx], slots[j][qj_idx] = slots[j][qj_idx], slots[i][qi_idx]

        if not improved:
            break


def _slot_error(slot_qs: List[Question], blueprint: dict) -> float:
    """Calculate how far a slot's distribution is from the blueprint."""
    if not blueprint or not slot_qs:
        return 0.0

    total = len(slot_qs)
    error = 0.0

    for dim_key, attr in [("bloom_distribution", "bloom_level"), ("difficulty_distribution", "difficulty")]:
        bp_dist = blueprint.get(dim_key, {})
        actual_dist = {}
        for q in slot_qs:
            val = getattr(q, attr, None) or "Uncategorized"
            actual_dist[val] = actual_dist.get(val, 0) + 1

        for category, target_pct in bp_dist.items():
            target_count = (target_pct / 100.0) * total if target_pct > 1 else target_pct * total
            actual_count = actual_dist.get(category, 0)
            error += abs(actual_count - target_count)

    return error


def _calculate_blueprint_match(bloom_dist, diff_dist, topic_dist, total, blueprint):
    """Calculate how well a slot matches the blueprint (0.0 = worst, 1.0 = perfect)."""
    if not blueprint or total == 0:
        return None

    total_categories = 0
    match_sum = 0.0

    for dist, bp_key in [(bloom_dist, "bloom_distribution"), (diff_dist, "difficulty_distribution")]:
        bp_dist = blueprint.get(bp_key, {})
        for category, target_pct in bp_dist.items():
            target_count = (target_pct / 100.0) * total if target_pct > 1 else target_pct * total
            actual_count = dist.get(category, 0)
            if target_count > 0:
                ratio = min(actual_count / target_count, 1.0)
                match_sum += ratio
                total_categories += 1

    return match_sum / total_categories if total_categories > 0 else None
