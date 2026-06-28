export type StatsResponse = {
  total_transactions: number;
  total_amount: number;
  average_amount: number;
  anomalies_count: number;
  failure_rate: number;
  by_type: Record<string, number>;
  by_channel: Record<string, number>;
};

export type TimeseriesResponse = {
  transactions_by_day: Array<{ day: string; transactions: number }>;
  amounts_by_day: Array<{ day: string; total_amount: number }>;
  amounts_by_hour: Array<{ hour: number; total_amount: number }>;
  anomalies_by_hour: Array<{ hour: number; anomalies: number }>;
  anomalies_by_week: Array<{ week: string; anomalies: number }>;
  hourly_heatmap: Array<{ day_of_week: string; hour: number; transactions: number }>;
  volume_by_operator: Array<{ operator: string; transactions: number }>;
  volume_by_wilaya: Array<{ wilaya: string; transactions: number }>;
};

export type GeoWilaya = {
  wilaya: string;
  transactions: number;
  total_amount: number;
  anomalies_count: number;
  failure_rate: number;
};

export type GeoResponse = {
  wilayas: GeoWilaya[];
};

export type ModelStatus = {
  algorithm: string;
  trained: boolean;
  path: string;
  parameters: Record<string, unknown>;
};

export type ModelStatusResponse = {
  available_algorithms: string[];
  models: ModelStatus[];
  metadata: Record<string, unknown>;
};

export type HealthResponse = {
  status: string;
  module: string;
};

export type ApiSnapshot = {
  stats: StatsResponse;
  timeseries: TimeseriesResponse;
  geo: GeoResponse;
  models: ModelStatusResponse;
};

export type IngestResponse = {
  rows: number;
  valid_rows: number;
  invalid_rows: number;
  dataset_path: string;
  errors_file: string | null;
};

export type PredictionPreview = {
  transaction_id?: string;
  timestamp?: string;
  amount?: number;
  transaction_type?: string;
  channel?: string;
  anomaly_type?: string;
  operator?: string;
  status?: string;
  sender_wilaya?: string;
  receiver_wilaya?: string;
  anomaly_label?: number;
  anomaly_score?: number;
  business_rule_reasons?: string;
  algorithm?: string;
};

export type ModelPredictionResult = {
  algorithm: "isolation_forest" | "lof" | "autoencoder" | "ensemble";
  total_transactions: number;
  anomalies_detected: number;
  output_path: string;
  preview: PredictionPreview[];
};

export type PredictAllResponse = {
  status: string;
  data_path: string;
  results: ModelPredictionResult[];
};

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? DEFAULT_API_BASE_URL;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    const isFormData = init?.body instanceof FormData;
    response = await fetch(`${apiBaseUrl}${path}`, {
      headers: isFormData
        ? init?.headers
        : {
            "Content-Type": "application/json",
            ...init?.headers,
          },
      ...init,
    });
  } catch (error) {
    throw new Error(
      `API FastAPI inaccessible sur ${apiBaseUrl}. Lance le backend ou vérifie le CORS.`,
    );
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function datasetQuery(datasetPath: string): string {
  return `dataset_path=${encodeURIComponent(datasetPath)}`;
}

export const apiClient = {
  uploadDataset(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request<IngestResponse>("/ingest", {
      method: "POST",
      body: formData,
    });
  },

  predictAll(dataPath: string) {
    return request<PredictAllResponse>("/detect/predict-all", {
      method: "POST",
      body: JSON.stringify({ data_path: dataPath }),
    });
  },

  getStats(datasetPath: string) {
    return request<StatsResponse>(`/stats?${datasetQuery(datasetPath)}`);
  },

  getTimeseries(datasetPath: string) {
    return request<TimeseriesResponse>(`/timeseries?${datasetQuery(datasetPath)}`);
  },

  getGeo(datasetPath: string) {
    return request<GeoResponse>(`/geo?${datasetQuery(datasetPath)}`);
  },

  getModels() {
    return request<ModelStatusResponse>("/detect/models");
  },

  getHealth(module: "stats" | "timeseries" | "geo" | "ingest") {
    return request<HealthResponse>(`/${module}/health`);
  },

  async getSnapshot(datasetPath: string): Promise<ApiSnapshot> {
    const [stats, timeseries, geo, models] = await Promise.all([
      this.getStats(datasetPath),
      this.getTimeseries(datasetPath),
      this.getGeo(datasetPath),
      this.getModels(),
    ]);

    return { stats, timeseries, geo, models };
  },
};
