from __future__ import annotations

from pathlib import Path

from mauripay.detection.iforest import IsolationForestDetector
from mauripay.detection.lof import LOFDetector


MODEL_FILENAMES = {
    "isolation_forest": "isolation_forest.joblib",
    "lof": "lof.joblib",
}

DETECTOR_CLASSES = {
    "isolation_forest": IsolationForestDetector,
    "lof": LOFDetector,
}


def model_path(model_dir: str | Path, algorithm: str) -> Path:
    if algorithm not in MODEL_FILENAMES:
        choices = ", ".join(sorted(MODEL_FILENAMES))
        raise ValueError(f"Unknown algorithm '{algorithm}'. Choose one of: {choices}")
    return Path(model_dir) / MODEL_FILENAMES[algorithm]


def load_detector(model_dir: str | Path, algorithm: str):
    return DETECTOR_CLASSES[algorithm].load(model_path(model_dir, algorithm))
