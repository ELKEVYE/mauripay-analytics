from __future__ import annotations

from typing import Self

import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor

from mauripay.detection.base import BaseDetector


class LOFDetector(BaseDetector):
    algorithm = "lof"

    def __init__(
        self,
        n_neighbors: int = 20,
        contamination: float | str = 0.02,
        metric: str = "minkowski",
    ) -> None:
        self.n_neighbors = n_neighbors
        self.contamination = contamination
        self.metric = metric
        self.model = LocalOutlierFactor(
            n_neighbors=n_neighbors,
            contamination=contamination,
            metric=metric,
            novelty=True,
        )

    def fit(self, X: np.ndarray) -> Self:
        if X.shape[0] <= self.n_neighbors:
            raise ValueError(
                "LOF requires more rows than n_neighbors. "
                f"Got {X.shape[0]} rows and n_neighbors={self.n_neighbors}."
            )
        self.model.fit(X)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        raw = self.model.predict(X)
        return (raw == -1).astype(int)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        return -self.model.score_samples(X)

    def results(self, X: np.ndarray) -> pd.DataFrame:
        """Reuse one nearest-neighbor query for labels and anomaly scores."""
        self.model.n_jobs = -1
        raw_scores = self.model.score_samples(X)
        labels = (raw_scores < self.model.offset_).astype(int)
        return pd.DataFrame(
            {
                "anomaly_label": labels,
                "anomaly_score": -raw_scores,
                "algorithm": self.algorithm,
            }
        )

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "n_neighbors": self.n_neighbors,
            "contamination": self.contamination,
            "metric": self.metric,
            "novelty": True,
        }
