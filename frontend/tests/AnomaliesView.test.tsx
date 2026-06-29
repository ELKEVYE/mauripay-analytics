import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ModelPredictionResult } from "../src/api/client";
import { AnomaliesView } from "../src/views/AnomaliesView";

const results: ModelPredictionResult[] = [
  {
    algorithm: "ensemble",
    total_transactions: 2,
    anomalies_detected: 2,
    output_path: "outputs/ensemble.csv",
    preview: [{
      transaction_id: "TX-IF",
      timestamp: "2026-01-01T10:00:00Z",
      amount: 150000,
      anomaly_score: 0.91,
      anomaly_type: "HIGH_AMOUNT",
      sender_wilaya: "Trarza",
      operator: "Bankily",
      status: "SUCCESS",
    }, {
      transaction_id: "TX-LOF",
      timestamp: "2026-01-02T10:00:00Z",
      amount: 5000,
      anomaly_score: 0.82,
      anomaly_type: "HIGH_FREQUENCY",
      sender_wilaya: "Nouakchott-Ouest",
      operator: "Masrvi",
      status: "FAILED",
    }],
  },
];

function buildLargeResults(total: number): ModelPredictionResult[] {
  return [{
    algorithm: "ensemble",
    total_transactions: total,
    anomalies_detected: total,
    output_path: "outputs/ensemble.csv",
    preview: Array.from({ length: total }, (_, index) => ({
      transaction_id: `TX-${index}`,
      timestamp: "2026-01-01T10:00:00Z",
      amount: 1000 + index,
      anomaly_score: 0.9,
      anomaly_type: "HIGH_AMOUNT",
      sender_wilaya: "Trarza",
      operator: "Bankily",
      status: "SUCCESS",
    })),
  }];
}

test("anomalies view displays the suspicious transactions table", () => {
  render(<AnomaliesView results={results} />);

  expect(screen.getByText("Filtres")).toBeInTheDocument();
  expect(screen.queryByText("Transactions suspectes")).not.toBeInTheDocument();
  expect(screen.getByText("TX-IF")).toBeInTheDocument();
  expect(screen.getByText("TX-LOF")).toBeInTheDocument();
  expect(screen.getAllByText("High amount").length).toBeGreaterThan(0);
  expect(screen.queryByLabelText("Filtrer par modèle")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Filtrer par type d’anomalie")).not.toBeInTheDocument();
});

test("anomalies filters and drill-down work", async () => {
  const user = userEvent.setup();
  render(<AnomaliesView results={results} />);

  await user.selectOptions(screen.getByLabelText("Filtrer par opérateur"), "Masrvi");
  expect(screen.queryByText("TX-IF")).not.toBeInTheDocument();
  expect(screen.getByText("TX-LOF")).toBeInTheDocument();

  await user.click(screen.getByLabelText("Voir TX-LOF"));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  expect(screen.getByText("Pourquoi cette transaction est suspecte")).toBeInTheDocument();

  await user.click(screen.getByLabelText("Fermer les details"));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("anomalies table paginates large result sets", async () => {
  const user = userEvent.setup();
  render(<AnomaliesView results={buildLargeResults(105)} />);

  expect(screen.getByText("TX-0")).toBeInTheDocument();
  expect(screen.queryByText("TX-100")).not.toBeInTheDocument();
  expect(screen.getByText("Page 1 / 2")).toBeInTheDocument();

  await user.click(screen.getByText("Suivant"));

  expect(screen.getByText("TX-100")).toBeInTheDocument();
  expect(screen.queryByText("TX-0")).not.toBeInTheDocument();
  expect(screen.getByText("Page 2 / 2")).toBeInTheDocument();
});

