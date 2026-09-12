import type { ReactNode } from "react";

/**
 * Shared chart language. Two data colours (anchor blue, accent cyan) plus a
 * muted tertiary; `alert` red is used only on the anomaly views. Categorical
 * breakdowns use a single-hue anchor ramp so a chart reads as one family.
 */
export const CHART = {
  anchor: "#2457C5",
  accent: "#0E7490",
  muted: "#8B9DB9",
  alert: "#B42332",
  grid: "#E5EBF4",
  axis: "#52647C",
  anchorRamp: ["#2457C5", "#4C75CF", "#7B9BDD", "#A6BCEA", "#D2DDF5", "#0E7490"],
  alertRamp: ["#B42332", "#D36A75", "#EAB3BA"],
} as const;

export const axisProps = {
  axisLine: false,
  tickLine: false,
  tick: { fill: CHART.axis, fontSize: 11 },
} as const;

type TooltipEntry = {
  name?: ReactNode;
  value?: number | string;
  color?: string;
  dataKey?: string | number;
};

type ChartTooltipProps = {
  active?: boolean;
  label?: ReactNode;
  payload?: TooltipEntry[];
  /** Formats the numeric value; defaults to fr-FR grouping. */
  format?: (value: number) => string;
};

const defaultFormat = (value: number) => value.toLocaleString("fr-FR");

export function ChartTooltip({ active, label, payload, format = defaultFormat }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-[10px] border border-hairline bg-surface px-3 py-2 shadow-pop">
      {label != null && label !== "" ? (
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.06em] text-ink-muted">
          {label}
        </p>
      ) : null}
      <div className="space-y-0.5">
        {payload.map((entry, index) => (
          <div key={`${String(entry.dataKey ?? index)}`} className="flex items-center gap-2 text-xs">
            <span
              aria-hidden="true"
              className="h-2 w-2 shrink-0 rounded-[2px]"
              style={{ background: entry.color ?? CHART.anchor }}
            />
            {entry.name != null ? <span className="text-ink-muted">{entry.name}</span> : null}
            <span className="tnum ml-auto font-medium text-ink">
              {typeof entry.value === "number" ? format(entry.value) : entry.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export const tooltipCursor = { fill: "rgba(36, 87, 197, 0.06)" } as const;
