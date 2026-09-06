import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type React from "react";
import App from "../src/App";

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  CircleMarker: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Popup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("react-plotly.js", () => ({
  default: () => <div data-testid="plotly-chart" />,
}));

test("renders dashboard cards and navigates via the top nav", async () => {
  const user = userEvent.setup();
  render(<App />);

  expect(screen.getByText(/MauriPay/)).toBeInTheDocument();
  expect(screen.getAllByText("Transactions").length).toBeGreaterThan(0);
  expect(screen.getByText("Montant total")).toBeInTheDocument();
  expect(screen.getByText("Fraudes détectées")).toBeInTheDocument();
  expect(screen.getAllByText("Taux d'échec").length).toBeGreaterThan(0);
  expect(screen.getByText("Fichier de transactions")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "0 anomalies détectées" }));
  expect(screen.getByText("Notifications")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Voir les transactions suspectes" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Transactions" }));
  await user.click(screen.getByRole("button", { name: /Opérations/ }));
  expect(screen.getByText("Heatmap horaire")).toBeInTheDocument();
  expect(screen.queryByText("Fichier de transactions")).not.toBeInTheDocument();
  expect(screen.queryByText("Montant total")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Anomalies" }));
  await user.click(screen.getByRole("button", { name: /Transactions suspectes/ }));
  expect(screen.getByText("Televersez un fichier pour afficher les transactions suspectes.")).toBeInTheDocument();
});
