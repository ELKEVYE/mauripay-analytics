from __future__ import annotations

import logging
import time
from importlib import import_module
from pathlib import Path
from typing import Any, Self

import numpy as np
import pandas as pd

from mauripay.detection.base import BaseDetector


logger = logging.getLogger(__name__)

try:
    torch: Any = import_module("torch")
    nn: Any = import_module("torch.nn")
    torch_data: Any = import_module("torch.utils.data")
    DataLoader: Any = torch_data.DataLoader
    TensorDataset: Any = torch_data.TensorDataset
except ImportError:  # pragma: no cover - keeps non-autoencoder detection usable
    torch = None
    nn = None
    DataLoader = None
    TensorDataset = None


def _require_torch() -> None:
    if torch is None or nn is None:
        raise ImportError(
            "PyTorch is required to use AutoencoderDetector. "
            "Install the backend dependencies including 'torch'."
        )


if nn is not None:

    class AutoencoderNet(nn.Module):
        """Simple encoder-decoder network for transaction reconstruction."""

        def __init__(
            self,
            input_dim: int,
            encoding_dim: int = 8,
            hidden_dims: list[int] | tuple[int, int] = (32, 16),
        ) -> None:
            super().__init__()
            hidden_dims = tuple(hidden_dims)
            if input_dim <= 0:
                raise ValueError("input_dim must be positive")
            if encoding_dim <= 0:
                raise ValueError("encoding_dim must be positive")
            if len(hidden_dims) != 2 or any(dim <= 0 for dim in hidden_dims):
                raise ValueError("hidden_dims must contain two positive integers")

            first_hidden, second_hidden = hidden_dims
            self.input_dim = input_dim
            self.encoding_dim = encoding_dim
            self.hidden_dims = hidden_dims

            self.encoder = nn.Sequential(
                nn.Linear(input_dim, first_hidden),
                nn.ReLU(),
                nn.Linear(first_hidden, second_hidden),
                nn.ReLU(),
                nn.Linear(second_hidden, encoding_dim),
                nn.ReLU(),
            )
            self.decoder = nn.Sequential(
                nn.Linear(encoding_dim, second_hidden),
                nn.ReLU(),
                nn.Linear(second_hidden, first_hidden),
                nn.ReLU(),
                nn.Linear(first_hidden, input_dim),
            )

        def forward(self, X: Any) -> Any:
            encoded = self.encoder(X)
            return self.decoder(encoded)

else:

    class AutoencoderNet:  # type: ignore[no-redef]
        def __init__(self, *args: object, **kwargs: object) -> None:
            _require_torch()


class AutoencoderDetector(BaseDetector):
    """PyTorch autoencoder detector compatible with the detection API."""

    algorithm = "autoencoder"

    def __init__(
        self,
        encoding_dim: int = 8,
        hidden_dims: list[int] | tuple[int, int] = (32, 16),
        learning_rate: float = 1e-3,
        epochs: int = 50,
        batch_size: int = 128,
        threshold_percentile: float = 98.0,
        random_state: int | None = 42,
        device: str | None = None,
    ) -> None:
        hidden_dims = tuple(hidden_dims)
        if encoding_dim <= 0:
            raise ValueError("encoding_dim must be positive")
        if len(hidden_dims) != 2 or any(dim <= 0 for dim in hidden_dims):
            raise ValueError("hidden_dims must contain two positive integers")
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if epochs <= 0:
            raise ValueError("epochs must be positive")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not 0 < threshold_percentile < 100:
            raise ValueError("threshold_percentile must be between 0 and 100")
        if device not in {None, "cpu", "cuda"}:
            raise ValueError("device must be one of: None, 'cpu', 'cuda'")

        self.encoding_dim = encoding_dim
        self.hidden_dims = hidden_dims
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.threshold_percentile = threshold_percentile
        self.random_state = random_state
        self.device = device
        self.model: AutoencoderNet | None = None
        self.threshold_: float | None = None
        self.input_dim_: int | None = None
        self.training_loss_: list[float] = []

    @staticmethod
    def _validate_X(X: np.ndarray) -> np.ndarray:
        array = np.asarray(X, dtype=np.float32)
        if array.ndim != 2:
            raise ValueError("X must be a 2D numpy array")
        if array.shape[0] == 0 or array.shape[1] == 0:
            raise ValueError("X must contain at least one row and one feature")
        if not np.isfinite(array).all():
            raise ValueError("X must contain only finite numeric values")
        return array

    def _torch_device(self):
        _require_torch()
        if self.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "AutoencoderDetector requested device='cuda', but CUDA is not available"
            )
        return torch.device(self.device or ("cuda" if torch.cuda.is_available() else "cpu"))

    def _reconstruction_errors(self, X: np.ndarray) -> np.ndarray:
        _require_torch()
        if self.model is None:
            raise RuntimeError("AutoencoderDetector is not fitted. Call fit() first.")

        array = self._validate_X(X)
        if self.input_dim_ is not None and array.shape[1] != self.input_dim_:
            raise ValueError(
                f"X has {array.shape[1]} features, but this autoencoder was fitted "
                f"with {self.input_dim_} features"
            )
        device = self._torch_device()
        self.model.to(device)
        self.model.eval()
        with torch.no_grad():
            tensor = torch.from_numpy(array).to(device)
            reconstructed = self.model(tensor)
            errors = torch.mean((tensor - reconstructed) ** 2, dim=1)
        return errors.detach().cpu().numpy()

    def fit(self, X: np.ndarray) -> Self:
        _require_torch()
        array = self._validate_X(X)
        if self.random_state is not None:
            torch.manual_seed(self.random_state)
            np.random.seed(self.random_state)

        self.input_dim_ = array.shape[1]
        self.model = AutoencoderNet(
            input_dim=self.input_dim_,
            encoding_dim=self.encoding_dim,
            hidden_dims=self.hidden_dims,
        )

        device = self._torch_device()
        self.model.to(device)
        dataset = TensorDataset(torch.from_numpy(array))
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        criterion = nn.MSELoss()

        self.training_loss_ = []
        self.model.train()
        logger.info(
            "Autoencoder training started: "
            "samples=%s, features=%s, epochs=%s, batch_size=%s, "
            "batches_per_epoch=%s, device=%s",
            len(dataset),
            self.input_dim_,
            self.epochs,
            self.batch_size,
            len(loader),
            device,
        )
        for epoch_index in range(self.epochs):
            epoch_started_at = time.perf_counter()
            epoch_loss = 0.0
            for (batch,) in loader:
                batch = batch.to(device)
                optimizer.zero_grad()
                reconstructed = self.model(batch)
                loss = criterion(reconstructed, batch)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * batch.size(0)
            average_loss = epoch_loss / len(dataset)
            self.training_loss_.append(average_loss)
            elapsed_seconds = time.perf_counter() - epoch_started_at
            logger.info(
                "Epoch %s/%s completed - loss=%.6f - %.1fs",
                epoch_index + 1,
                self.epochs,
                average_loss,
                elapsed_seconds,
            )

        logger.info("Computing reconstruction threshold")
        errors = self._reconstruction_errors(array)
        self.threshold_ = float(np.percentile(errors, self.threshold_percentile))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.threshold_ is None:
            raise RuntimeError("AutoencoderDetector is not fitted. Call fit() first.")
        return (self.score_samples(X) > self.threshold_).astype(int)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        return self._reconstruction_errors(X)

    def results(self, X: np.ndarray) -> pd.DataFrame:
        """Calculate reconstruction errors once and derive labels from them."""
        if self.threshold_ is None:
            raise RuntimeError("AutoencoderDetector is not fitted. Call fit() first.")
        scores = self.score_samples(X)
        return pd.DataFrame(
            {
                "anomaly_label": (scores > self.threshold_).astype(int),
                "anomaly_score": scores,
                "algorithm": self.algorithm,
            }
        )

    def save(self, path: str | Path) -> Path:
        return super().save(path)

    @classmethod
    def load(cls, path: str | Path) -> Self:
        return super().load(path)

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "encoding_dim": self.encoding_dim,
            "hidden_dims": self.hidden_dims,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "threshold_percentile": self.threshold_percentile,
            "random_state": self.random_state,
            "device": self.device,
            "threshold": self.threshold_,
            "input_dim": self.input_dim_,
            "training_loss_last": (
                self.training_loss_[-1] if self.training_loss_ else None
            ),
            "training_loss_epochs": len(self.training_loss_),
        }
