import type { ReactNode } from "react";

/**
 * Shared chart language. Two data colours (anchor green, accent gold) plus a
 * muted tertiary; `alert` red is used only on the anomaly views. Categorical
 * breakdowns use a single-hue anchor ramp so a chart reads as one family.
 */
export const CHART = {
  anchor: "#0C5C4C",
  accent: "#A67C3D",
  muted: "#8CA6A0",
  alert: "#B42318",
  grid: "#EAEDEC",
  axis: "#5C6B65",
  anchorRamp: ["#0C5C4C", "#3D7A6C", "#6B9B8F", "#9CBDB4", "#C9D9D4", "#A67C3D"],
  alertRamp: ["#B42318", "#D0685C", "#E8B3AC"],
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

export const tooltipCursor = { fill: "rgba(12, 92, 76, 0.06)" } as const;
