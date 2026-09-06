import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";
import { MapPinned } from "lucide-react";
import type { GeoWilaya } from "../api/client";

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
      className={`dashboard-card overflow-hidden border-emerald-100 bg-gradient-to-br from-white via-white to-emerald-50/40 ${
        compact ? "geo-map-compact flex min-h-[380px] flex-col lg:min-h-0" : ""
      }`}
    >
      <header className={`flex shrink-0 items-start gap-3 border-b border-slate-200/80 bg-white/70 ${compact ? "px-3 py-3" : "px-4 py-3.5"}`}>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-emerald-50 text-mauri-green">
          <MapPinned className="h-[18px] w-[18px]" aria-hidden="true" />
        </span>
        <div>
          <h2 className={`${compact ? "text-sm" : "text-base"} font-extrabold text-ink`}>Carte des wilayas</h2>
          <p className="mt-0.5 text-xs font-medium text-slate-500">Volume et anomalies par zone</p>
        </div>
      </header>
      <MapContainer
        center={[18.2, -12.6]}
        className={compact ? "flex-1" : undefined}
        zoom={5}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {wilayas.map((item) => {
          const position = WILAYA_COORDINATES[item.wilaya];
          if (!position) return null;
          const anomalyRatio = item.anomalies_count / maxAnomalies;
          const markerColor = anomalyRatio > 0.65 ? "#dc2626" : anomalyRatio > 0.25 ? "#f59e0b" : "#4338ca";

          return (
            <CircleMarker
              center={position}
              key={item.wilaya}
              pathOptions={{
                color: markerColor,
                fillColor: markerColor,
                fillOpacity: 0.5,
                opacity: 0.95,
                weight: 3,
              }}
              radius={7 + (item.transactions / maxTransactions) * 20}
            >
              <Tooltip direction="top" opacity={0.95}>
                <div className="text-xs">
                  <strong>{item.wilaya}</strong>
                  <br />
                  {formatNumber(item.transactions)} transactions
                  <br />
                  {formatNumber(item.anomalies_count)} anomalies
                </div>
              </Tooltip>
              <Popup>
                <div className="min-w-[190px] text-sm">
                  <strong className="text-ink">{item.wilaya}</strong>
                  <div className="mt-2 grid gap-1 text-slate-600">
                    <span>Transactions: {formatNumber(item.transactions)}</span>
                    <span>Montant: {formatAmount(item.total_amount)}</span>
                    <span>Anomalies: {formatNumber(item.anomalies_count)}</span>
                    <span>Taux d'echec: {formatPercent(item.failure_rate)}</span>
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
