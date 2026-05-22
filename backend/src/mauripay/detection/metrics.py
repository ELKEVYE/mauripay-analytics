from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_detection(
    y_true: list[int] | np.ndarray,
    y_pred: list[int] | np.ndarray,
    y_score: list[float] | np.ndarray | None = None,
) -> dict[str, object]:
    y_true_array = np.asarray(y_true).astype(int)
    y_pred_array = np.asarray(y_pred).astype(int)

    metrics: dict[str, object] = {
        "precision": precision_score(y_true_array, y_pred_array, zero_division=0),
        "recall": recall_score(y_true_array, y_pred_array, zero_division=0),
        "f1_score": f1_score(y_true_array, y_pred_array, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true_array, y_pred_array).tolist(),
    }

    if y_score is not None and len(set(y_true_array.tolist())) == 2:
        metrics["roc_auc"] = roc_auc_score(y_true_array, np.asarray(y_score))

    return metrics
