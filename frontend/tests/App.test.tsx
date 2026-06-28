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

test("renders dashboard cards and navigates between analysis pages", async () => {
  const user = userEvent.setup();
  render(<App />);

  expect(screen.getAllByText("MauriPay Analytics").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Transactions").length).toBeGreaterThan(0);
  expect(screen.getByText("Montant total")).toBeInTheDocument();
  expect(screen.getByText("Consensus des trois modèles")).toBeInTheDocument();
  expect(screen.getAllByText("Taux d'échec").length).toBeGreaterThan(0);
  expect(screen.getByText("Fichier de transactions")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Actualiser les données" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Réduire la sidebar" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Activer le mode sombre" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Réduire la sidebar" }));
  expect(screen.getByRole("button", { name: "Agrandir la sidebar" })).toBeInTheDocument();
  expect(screen.getByTestId("app-sidebar")).toHaveClass("lg:w-20");
  expect(screen.getByTestId("app-header")).toHaveClass("lg:left-20");
  expect(screen.getByTestId("app-content")).toHaveClass("lg:pl-20");

  await user.click(screen.getByRole("button", { name: "Activer le mode sombre" }));
  expect(screen.getByRole("button", { name: "Activer le mode clair" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "0 anomalies détectées" }));
  expect(screen.getByText("Notifications")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Voir les anomalies" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /Operations/ }));
  expect(screen.getByText("Heatmap horaire")).toBeInTheDocument();
  expect(screen.queryByText("Fichier de transactions")).not.toBeInTheDocument();
  expect(screen.queryByText("Montant total")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /Transactions suspectes/ }));
  expect(screen.getByText("Televersez un fichier pour afficher les transactions suspectes.")).toBeInTheDocument();
});


