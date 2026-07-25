"""
shap_explainer.py  —  SkillScavenge SHAP Explainability Engine
===============================================================
Computes per-prediction SHAP feature contributions for the XGBoost salary regressor.
Strictly additive — does not modify training, models, or saved binaries.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import shap

_EXPLAINER: Optional[shap.TreeExplainer] = None


def get_tree_explainer(model: Any) -> shap.TreeExplainer:
    """Get or initialize a cached shap.TreeExplainer instance."""
    global _EXPLAINER
    if _EXPLAINER is None:
        _EXPLAINER = shap.TreeExplainer(model)
    return _EXPLAINER


def compute_prediction_shap(
    model: Any,
    feature_vector: List[float],
    feature_names: List[str],
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    Compute SHAP feature contributions for a single input feature vector.

    Returns:
        Dict containing base_value_log and list of feature contributions.
    """
    explainer = get_tree_explainer(model)
    X = np.array([feature_vector], dtype=np.float32)

    shap_vals = explainer.shap_values(X)
    if len(shap_vals.shape) > 1:
        shap_vals = shap_vals[0]

    base_val = float(explainer.expected_value)

    contributions = []
    for name, val, contrib in zip(feature_names, feature_vector, shap_vals):
        contributions.append({
            "feature": name,
            "value": float(val),
            "shap_value": round(float(contrib), 4),
        })

    # Sort by absolute SHAP impact
    contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

    return {
        "base_value_log": round(base_val, 4),
        "feature_contributions": contributions[:top_n],
    }
