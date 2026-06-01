from __future__ import annotations

from pathlib import Path
from typing import Self

import numpy as np

from mauripay.detection.base import BaseDetector


class AutoencoderDetector(BaseDetector):
    """
    Reserved detector slot for the Month 3 Autoencoder.

    Your friend can implement this class while keeping the same public contract
    as IsolationForestDetector and LOFDetector: fit, predict, score_samples,
    save, and load.
    """

    algorithm = "autoencoder"

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None

    def fit(self, X: np.ndarray) -> Self:
        raise NotImplementedError("Autoencoder training is not implemented yet.")

    def predict(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError("Autoencoder prediction is not implemented yet.")

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError("Autoencoder scoring is not implemented yet.")
