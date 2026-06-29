from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DetectionModel = Literal["isolation_forest", "lof", "autoencoder", "ensemble"]


class HealthResponse(BaseModel):
    status: str
    module: str


class GenerateDatasetRequest(BaseModel):
    rows: int = Field(10_000, gt=0, le=1_000_000)
    output_path: str = Field("data/generated/api_generated_10k.csv")
    accounts: int = Field(1_000, gt=1)
    start_date: str = "2026-01-01"
    end_date: str = "2026-12-31"
    seed: int | None = 42
    anomaly_rate: float = Field(0.02, ge=0, le=1)
    tontine_rate: float = Field(0.001, ge=0, le=1)
    structuring_rate: float = Field(0.003, ge=0, le=1)
    high_frequency_rate: float = Field(0.002, ge=0, le=1)


class GenerateDatasetResponse(BaseModel):
    status: str
    rows: int
    output_path: str
    stats: dict[str, Any]


class IngestResponse(BaseModel):
    rows: int
    valid_rows: int
    invalid_rows: int
    dataset_path: str
    errors_file: str | None = None


class TrainRequest(BaseModel):
    data_path: str = Field(..., description="CSV/JSON/Parquet path, relative to backend or absolute")
    contamination: float = Field(0.02, gt=0, lt=1)
    n_estimators: int = Field(100, ge=1)
    max_samples: str = "auto"
    random_state: int = 42
    n_neighbors: int = Field(20, ge=1)
    metric: str = "minkowski"
    test_size: float = Field(0.0, ge=0, lt=1)
    split_seed: int = 42
    include_autoencoder: bool = False
    lof_max_train_rows: int | None = Field(20000, ge=0)
    autoencoder_epochs: int = Field(10, ge=1)
    autoencoder_batch_size: int = Field(256, ge=1)
    autoencoder_threshold_percentile: float = Field(98.0, gt=0, lt=100)
    autoencoder_optimize_threshold: bool = True
    autoencoder_device: str | None = None
    model_dir: str | None = None
    output_dir: str | None = None



class PredictRequest(BaseModel):
    algorithm: DetectionModel
    data_path: str = Field(..., description="CSV/JSON/Parquet path, relative to backend or absolute")
    output_path: str | None = Field(None, description="Optional CSV output path")
    model_dir: str | None = Field(None, description="Optional model directory")


class PredictAllRequest(BaseModel):
    data_path: str = Field(
        ...,
        description="Uploaded CSV/JSON/Parquet path, relative to backend or absolute",
    )


class DetectionRunResponse(BaseModel):
    status: str
    algorithm: str
    rows: int
    output_path: str
    anomaly_count: int
    total_transactions: int
    anomalies_detected: int
    results_path: str
    evaluation: dict[str, Any] | None = None
    preview: list[dict[str, Any]]


class ModelPredictionSummary(BaseModel):
    algorithm: str
    total_transactions: int
    anomalies_detected: int
    output_path: str
    preview: list[dict[str, Any]]


class PredictAllResponse(BaseModel):
    status: str
    data_path: str
    results: list[ModelPredictionSummary]


class ModelStatusResponse(BaseModel):
    available_algorithms: list[str]
    models: list[dict[str, Any]]
    metadata: dict[str, Any]


class TrainResponse(BaseModel):
    status: str
    algorithms: list[str]
    metadata: dict[str, Any]


class StatsResponse(BaseModel):
    total_transactions: int
    total_amount: float
    average_amount: float
    anomalies_count: int
    failure_rate: float
    by_type: dict[str, int]
    by_channel: dict[str, int]


class TimeseriesResponse(BaseModel):
    transactions_by_day: list[dict[str, Any]]
    amounts_by_day: list[dict[str, Any]]
    amounts_by_hour: list[dict[str, Any]]
    anomalies_by_hour: list[dict[str, Any]]
    anomalies_by_week: list[dict[str, Any]]
    hourly_heatmap: list[dict[str, Any]]
    volume_by_operator: list[dict[str, Any]]
    volume_by_wilaya: list[dict[str, Any]]


class GeoWilayaAggregate(BaseModel):
    wilaya: str
    transactions: int
    total_amount: float
    anomalies_count: int
    failure_rate: float


class GeoResponse(BaseModel):
    wilayas: list[GeoWilayaAggregate]
