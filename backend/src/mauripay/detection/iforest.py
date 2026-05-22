from __future__ import annotations

from typing import Self

import numpy as np
from sklearn.ensemble import IsolationForest

from mauripay.detection.base import BaseDetector


class IsolationForestDetector(BaseDetector):
    algorithm = "isolation_forest"

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float | str = 0.02,
        random_state: int | None = 42,
        max_samples: int | float | str = "auto",
    ) -> None:
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.max_samples = max_samples
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
            max_samples=max_samples,
        )

    def fit(self, X: np.ndarray) -> Self:
        self.model.fit(X)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        raw = self.model.predict(X)
        return (raw == -1).astype(int)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        return -self.model.score_samples(X)

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "max_samples": self.max_samples,
        }
