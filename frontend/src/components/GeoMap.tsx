import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";
import { MapPinned } from "lucide-react";
import type { GeoWilaya } from "../api/client";
import { CHART } from "./ChartKit";

const WILAYA_COORDINATES: Record<string, [number, number]> = {
  "Nouakchott-Ouest": [18.083, -15.978],
  "Nouakchott-Nord": [18.132, -15.924],
  "Nouakchott-Sud": [18.014, -15.965],
  "Dakhlet Nouadhibou": [20.93, -17.034],
  "Hodh El Chargui": [16.616, -7.25],
  "Hodh El Gharbi": [16.65, -9.6],
  Assaba: [16.15, -11.4],
  Gorgol: [16.45, -12.83],
  Brakna: [17.03, -13.95],
  Trarza: [17.85, -14.8],
  Adrar: [20.5, -12.75],
  Tagant: [18.7, -10.85],
  Guidimakha: [15.3, -12.25],
  "Tiris Zemmour": [22.67, -12.73],
  Inchiri: [19.75, -15.0],
};

type GeoMapProps = {
  wilayas: GeoWilaya[];
  compact?: boolean;
};

export function GeoMap({ wilayas, compact = false }: GeoMapProps) {
  const maxTransactions = Math.max(...wilayas.map((item) => item.transactions), 1);
  const maxAnomalies = Math.max(...wilayas.map((item) => item.anomalies_count), 1);

  const formatNumber = (value: number) => value.toLocaleString("fr-FR");
  const formatAmount = (value: number) => `${formatNumber(Math.round(value))} MRU`;
  const formatPercent = (value: number) => `${(value * 100).toFixed(2)} %`;

  return (
    <section
      className={`dashboard-card overflow-hidden ${
        compact ? "geo-map-compact flex min-h-[380px] flex-col lg:min-h-0" : ""
      }`}
    >
      <header
        className={`flex shrink-0 items-start gap-3 border-b border-hairline ${
          compact ? "px-3 py-3" : "px-4 py-3.5"
        }`}
      >
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-anchor-weak text-anchor"
          aria-hidden="true"
        >
          <MapPinned className="h-[18px] w-[18px]" />
        </span>
        <div>
          <h2 className={`${compact ? "text-sm" : "text-[15px]"} font-semibold text-ink`}>
            Carte des wilayas
          </h2>
          <p className="mt-0.5 text-xs text-ink-muted">
            Taille = volume · rouge = concentration d'anomalies
          </p>
        </div>
      </header>
      <MapContainer
        center={[18.2, -12.6]}
        className={compact ? "flex-1" : undefined}
        zoom={5}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        {wilayas.map((item) => {
          const position = WILAYA_COORDINATES[item.wilaya];
          if (!position) return null;
          const anomalyRatio = item.anomalies_count / maxAnomalies;
          const elevated = anomalyRatio > 0.5;
          const markerColor = elevated ? CHART.alert : CHART.anchor;

          return (
            <CircleMarker
              center={position}
              key={item.wilaya}
              pathOptions={{
                color: markerColor,
                fillColor: markerColor,
                fillOpacity: elevated ? 0.45 : 0.28,
                opacity: 0.9,
                weight: 2,
              }}
              radius={6 + (item.transactions / maxTransactions) * 20}
            >
              <Tooltip direction="top" opacity={1}>
                <div className="text-xs">
                  <strong>{item.wilaya}</strong>
                  <br />
                  {formatNumber(item.transactions)} transactions
                  <br />
                  {formatNumber(item.anomalies_count)} anomalies
                </div>
              </Tooltip>
              <Popup>
                <div className="min-w-[190px] text-[13px]">
                  <strong className="text-ink">{item.wilaya}</strong>
                  <div className="mt-2 grid gap-1 text-ink-muted">
                    <span>Transactions : {formatNumber(item.transactions)}</span>
                    <span>Montant : {formatAmount(item.total_amount)}</span>
                    <span>Anomalies : {formatNumber(item.anomalies_count)}</span>
                    <span>Taux d'échec : {formatPercent(item.failure_rate)}</span>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </section>
  );
}
