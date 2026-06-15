from typing import Optional
import time
from app.repositories.questionnaire_repo import QuestionnaireRepository


# Simple TTL cache for questionnaire data
class QuestionnaireCache:
    """TTL cache for questionnaire weights and metadata."""
    
    def __init__(self, ttl_seconds: int = 600):  # 10 minutes default
        self.ttl = ttl_seconds
        self._cache = {}
    
    def get(self, key: str):
        """Get value from cache if not expired."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        timestamp, value = entry
        if time.time() - timestamp > self.ttl:
            # Expired
            del self._cache[key]
            return None
        return value
    
    def set(self, key: str, value):
        """Set value in cache with current timestamp."""
        self._cache[key] = (time.time(), value)
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()


# Global cache instance
_questionnaire_cache = QuestionnaireCache(ttl_seconds=600)  # 10 minutes


def _is_ordered_question(question_type: str, options: list) -> bool:
    """Determine if a question has ordered options vs categorical."""
    # If question_type explicitly indicates ordered, use that
    if question_type and question_type.lower() in ["ordered", "scale", "range"]:
        return True
    if question_type and question_type.lower() in ["categorical", "choice", "single_choice"]:
        return False
    # Otherwise, infer from options - if options suggest a natural order, treat as ordered
    # This is a heuristic - ideally question_type should be explicit
    return False


def _get_max_value(options: list) -> int:
    """
    Get the maximum value for an ordered question (0-indexed).
    
    For ordered questions with N options (0, 1, 2, ..., N-1), the max value is N-1.
    The similarity formula uses this as the denominator: 1.0 - abs(a - b) / max_val
    
    Example: options = [0, 1, 2, 3] (4 options)
    - max_val = 3
    - Difference 0: 1.0 - 0/3 = 1.0
    - Difference 1: 1.0 - 1/3 = 0.666
    - Difference 3: 1.0 - 3/3 = 0.0
    """
    if not options:
        return 3  # Default fallback
    return len(options) - 1


def sim(qid: int, a, b, question_metadata: dict, smoking_question_id: Optional[int] = None) -> float:
    """Calculate similarity between two answers for a specific question."""
    if qid == smoking_question_id:
        # Special handling for smoking question with penalty
        d = abs(a - b)
        if d <= 1:
            return 1.0
        if d == 2:
            return 0.1
        return 0.0

    meta = question_metadata.get(qid, {})
    question_type = meta.get("question_type", "")
    options = meta.get("options_en", []) or meta.get("options_ar", [])

    if _is_ordered_question(question_type, options):
        max_val = _get_max_value(options)
        return 1.0 - abs(a - b) / max_val if max_val > 0 else 1.0

    # Categorical: exact match required
    return 1.0 if a == b else 0.0


def weighted_similarity(
    answers_a: dict,
    answers_b: dict,
    weights: dict[int, float],
    question_metadata: dict,
    smoking_question_id: Optional[int] = None
) -> float:
    """
    Calculate weighted similarity between two users' questionnaire answers.
    
    Args:
        answers_a: User A's answers {question_id: answer_value}
        answers_b: User B's answers {question_id: answer_value}
        weights: Question weights {question_id: weight}
        question_metadata: Question metadata {question_id: {question_type, options, weight}}
        smoking_question_id: ID of the smoking question (if any)
    
    Returns:
        Weighted similarity score between 0 and 1
    """
    shared = set(answers_a.keys()) & set(answers_b.keys())
    if not shared:
        return 0.5

    total_w = 0.0
    total_sim = 0.0
    smoke_penalty = 1.0

    for qid_str in shared:
        qid = int(qid_str)
        w = weights.get(qid, 0.0)
        if w <= 0:
            continue  # Skip questions with zero or negative weight

        s = sim(qid, answers_a[qid_str], answers_b[qid_str], question_metadata, smoking_question_id)

        if qid == smoking_question_id and s < 0.5:
            smoke_penalty = 0.3

        total_sim += w * s
        total_w += w

    return (total_sim / total_w) * smoke_penalty if total_w > 0 else 0.5


def load_questionnaire_weights_and_metadata() -> tuple[dict[int, float], dict, Optional[int]]:
    """
    Load active question weights and metadata from database with caching.
    
    Uses a 10-minute TTL cache to avoid repeated database queries.
    
    Returns:
        tuple: (weights_dict, metadata_dict, smoking_question_id)
    """
    # Try to get from cache
    cached = _questionnaire_cache.get("weights_metadata")
    if cached is not None:
        return cached
    
    # Cache miss - load from database
    repo = QuestionnaireRepository()
    weights = repo.get_active_question_weights()
    metadata = repo.get_active_question_metadata()
    
    # Identify smoking question using matching_key
    smoking_question_id = None
    for qid, meta in metadata.items():
        matching_key = meta.get("matching_key")
        if matching_key == "smoking":
            smoking_question_id = qid
            break
    
    result = (weights, metadata, smoking_question_id)
    
    # Store in cache
    _questionnaire_cache.set("weights_metadata", result)
    
    return result


def clear_questionnaire_cache():
    """Clear the questionnaire cache. Useful for testing or after manual DB updates."""
    _questionnaire_cache.clear()