import { apiClient } from "../src/api/client";
import { vi } from "vitest";

test("client calls stats endpoint with encoded dataset path", async () => {
  const fetchMock = vi.fn(async () =>
    Response.json({
      total_transactions: 1,
      total_amount: 100,
      average_amount: 100,
      anomalies_count: 0,
      failure_rate: 0,
      by_type: {},
      by_channel: {},
    }),
  );
  globalThis.fetch = fetchMock;

  await apiClient.getStats("data/generated/mauripay_s_10k.csv");

  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining("/stats?dataset_path=data%2Fgenerated%2Fmauripay_s_10k.csv"),
    expect.any(Object),
  );
});

test("client uploads a local file as multipart data", async () => {
  const fetchMock = vi.fn(async (_url: RequestInfo | URL, _init?: RequestInit) =>
    Response.json({
      rows: 1,
      valid_rows: 1,
      invalid_rows: 0,
      dataset_path: "data/uploads/transactions_1234.csv",
      errors_file: null,
    }),
  );
  globalThis.fetch = fetchMock;

  await apiClient.uploadDataset(new File(["amount\n100"], "transactions.csv"));

  const [, init] = fetchMock.mock.calls[0];
  expect(init?.method).toBe("POST");
  expect(init?.body).toBeInstanceOf(FormData);
  expect(init?.headers).toBeUndefined();
});

test("client requests predictions from all models and the ensemble", async () => {
  const fetchMock = vi.fn(async () =>
    Response.json({
      status: "predicted",
      data_path: "data/uploads/transactions_1234.csv",
      results: [],
    }),
  );
  globalThis.fetch = fetchMock;

  await apiClient.predictAll("data/uploads/transactions_1234.csv");

  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining("/detect/predict-all"),
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ data_path: "data/uploads/transactions_1234.csv" }),
    }),
  );
});
