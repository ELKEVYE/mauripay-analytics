from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
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
        "accuracy": accuracy_score(y_true_array, y_pred_array),
        "confusion_matrix": confusion_matrix(y_true_array, y_pred_array).tolist(),
    }

    if y_score is not None and len(set(y_true_array.tolist())) == 2:
        metrics["roc_auc"] = roc_auc_score(y_true_array, np.asarray(y_score))

    return metrics


def evaluate_by_anomaly_type(
    anomaly_types: pd.Series,
    y_pred: list[int] | np.ndarray,
    y_score: list[float] | np.ndarray | None = None,
) -> dict[str, dict[str, object]]:
    """Evaluate binary anomaly predictions against each concrete anomaly type."""

    y_pred_array = np.asarray(y_pred).astype(int)
    results: dict[str, dict[str, object]] = {}

    for anomaly_type in sorted(set(anomaly_types.dropna().astype(str)) - {"NONE", ""}):
        y_true_type = (anomaly_types.astype(str) == anomaly_type).astype(int).to_numpy()
        metrics = evaluate_detection(y_true_type, y_pred_array, y_score)
        metrics["support"] = int(y_true_type.sum())
        results[anomaly_type] = metrics

    return results
