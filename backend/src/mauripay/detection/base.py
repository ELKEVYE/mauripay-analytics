from __future__ import annotations

from pathlib import Path
from typing import Protocol, Self

import joblib
import numpy as np
import pandas as pd


class DetectorProtocol(Protocol):
    algorithm: str

    def fit(self, X: np.ndarray) -> Self:
        ...

    def predict(self, X: np.ndarray) -> np.ndarray:
        ...

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        ...

    def save(self, path: str | Path) -> Path:
        ...


class BaseDetector:
    algorithm = "base"

    def fit(self, X: np.ndarray) -> Self:
        raise NotImplementedError

    def predict(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def results(self, X: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "anomaly_label": self.predict(X).astype(int),
                "anomaly_score": self.score_samples(X).astype(float),
                "algorithm": self.algorithm,
            }
        )

    def save(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, output_path)
        return output_path

    @classmethod
    def load(cls, path: str | Path) -> Self:
        model = joblib.load(Path(path))
        if not isinstance(model, cls):
            raise TypeError(
                f"Expected {cls.__name__} in {path}, got {type(model).__name__}"
            )
        return model
