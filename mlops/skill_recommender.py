"""
skill_recommender.py  —  SkillScavenge Semantic Skill Recommender Engine
========================================================================
Uses sentence-transformers (all-MiniLM-L6-v2) to generate 384-d dense embeddings
for master tech skills and compute cosine similarity recommendations.

Precomputes vectors once to models/skill_embeddings.joblib for sub-millisecond live queries.
Strictly additive — zero interaction with XGBoost model or training pipelines.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
EMBEDDINGS_FILE = BASE_DIR / "models" / "skill_embeddings.joblib"

_EMBEDDINGS_CACHE: Optional[Dict[str, np.ndarray]] = None


def generate_skill_embeddings(skill_names: List[str]) -> Dict[str, np.ndarray]:
    """Generate 384-d sentence-transformer embeddings for a list of skill names."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(skill_names, show_progress_bar=False)

    embedding_map = {}
    for name, vec in zip(skill_names, embeddings):
        norm = np.linalg.norm(vec)
        embedding_map[name] = (vec / norm) if norm > 0 else vec

    return embedding_map


def get_skill_embeddings(skill_names: Optional[List[str]] = None) -> Dict[str, np.ndarray]:
    """Get or load cached skill embeddings dictionary."""
    global _EMBEDDINGS_CACHE

    if _EMBEDDINGS_CACHE is not None:
        return _EMBEDDINGS_CACHE

    if EMBEDDINGS_FILE.exists():
        try:
            _EMBEDDINGS_CACHE = joblib.load(EMBEDDINGS_FILE)
            if skill_names and not all(s in _EMBEDDINGS_CACHE for s in skill_names):
                missing = [s for s in skill_names if s not in _EMBEDDINGS_CACHE]
                new_vecs = generate_skill_embeddings(missing)
                _EMBEDDINGS_CACHE.update(new_vecs)
                joblib.dump(_EMBEDDINGS_CACHE, EMBEDDINGS_FILE)
            return _EMBEDDINGS_CACHE
        except Exception:
            pass

    # Default fallback skills if none supplied
    if not skill_names:
        skill_names = [
            "Python", "SQL", "AWS", "Docker", "Kubernetes", "Machine Learning", 
            "Java", "React", "FastAPI", "PyTorch", "TensorFlow", "Git", "Linux", 
            "CI/CD", "Spark", "Hadoop", "Pandas", "Scikit-Learn", "Azure", "GCP",
            "Node.js", "TypeScript", "JavaScript", "C++", "Go"
        ]

    _EMBEDDINGS_CACHE = generate_skill_embeddings(skill_names)
    try:
        EMBEDDINGS_FILE.parent.mkdir(exist_ok=True)
        joblib.dump(_EMBEDDINGS_CACHE, EMBEDDINGS_FILE)
    except Exception:
        pass

    return _EMBEDDINGS_CACHE


def recommend_similar_skills(
    target_skill: str,
    all_skills: Optional[List[str]] = None,
    top_n: int = 8,
) -> List[Dict[str, Any]]:
    """
    Recommend top N semantically similar skills for a target skill using cosine similarity.
    """
    emb_map = get_skill_embeddings(all_skills)

    target_key = None
    for k in emb_map.keys():
        if k.lower().strip() == target_skill.lower().strip():
            target_key = k
            break

    if not target_key:
        from sentence_transformers import SentenceTransformer

        m = SentenceTransformer("all-MiniLM-L6-v2")
        vec = m.encode([target_skill])[0]
        norm = np.linalg.norm(vec)
        target_vec = (vec / norm) if norm > 0 else vec
        target_key = target_skill
    else:
        target_vec = emb_map[target_key]

    scores = []
    for name, vec in emb_map.items():
        if name.lower().strip() == target_key.lower().strip():
            continue
        sim = float(np.dot(target_vec, vec))
        scores.append({
            "skill": name,
            "similarity_score": round(sim, 4),
            "similarity_pct": round(max(0.0, sim) * 100, 1),
        })

    scores.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scores[:top_n]
