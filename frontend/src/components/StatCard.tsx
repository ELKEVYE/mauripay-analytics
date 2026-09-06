import { useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";

type StatCardProps = {
  title: string;
  value: string;
  detail: string;
  status: string;
  icon: LucideIcon;
  /** `alert` is reserved for the detected-fraud figure only. */
  tone?: "default" | "alert";
  nowrapValue?: boolean;
};

const toneClasses = {
  default: {
    topRule: "bg-anchor/70",
    icon: "bg-anchor-weak text-anchor",
    value: "text-ink",
  },
  alert: {
    topRule: "bg-alert/70",
    icon: "bg-alert-weak text-alert",
    value: "text-alert",
  },
} as const;

function parseDisplayValue(value: string) {
  if (value === "—" || value.trim() === "") {
    return null;
  }

  const match = value.match(/[\d\s .,]+/);
  if (!match) return null;

  const rawNumber = match[0];
  const normalized = rawNumber.replace(/[\s ]/g, "").replace(",", ".");
  const target = Number(normalized);
  if (!Number.isFinite(target)) return null;

  return {
    decimals: rawNumber.includes(".") || rawNumber.includes(",") ? 2 : 0,
    decimalSeparator: rawNumber.includes(".") ? "." : ",",
    prefix: value.slice(0, match.index ?? 0),
    suffix: value.slice((match.index ?? 0) + rawNumber.length),
    target,
  };
}

function CountUpValue({ value }: { value: string }) {
  const parsed = useMemo(() => parseDisplayValue(value), [value]);
  const reduceMotion = useReducedMotion();
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    if (!parsed || reduceMotion) {
      setDisplayValue(value);
      return;
    }

    const parsedValue = parsed;
    let frameId = 0;
    const duration = 600;
    const start = performance.now();
    const formatter = new Intl.NumberFormat("fr-FR", {
      maximumFractionDigits: parsedValue.decimals,
      minimumFractionDigits: parsedValue.decimals,
    });

    function tick(now: number) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = parsedValue.target * eased;
      const formatted =
        parsedValue.decimalSeparator === "."
          ? formatter.format(current).replace(",", ".")
          : formatter.format(current);
      setDisplayValue(`${parsedValue.prefix}${formatted}${parsedValue.suffix}`);

      if (progress < 1) {
        frameId = requestAnimationFrame(tick);
      }
    }

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [parsed, reduceMotion, value]);

  return <>{displayValue}</>;
}

export function StatCard({
  title,
  value,
  detail,
  status,
  icon: Icon,
  tone = "default",
  nowrapValue = false,
}: StatCardProps) {
  const colors = toneClasses[tone];

  return (
    <motion.section
      className="relative flex min-h-[132px] flex-col overflow-hidden rounded-xl border border-hairline bg-surface p-4 shadow-card transition-[box-shadow,border-color,transform] duration-150 hover:-translate-y-px hover:border-anchor/30 hover:shadow-card-hover"
      variants={{
        hidden: { opacity: 0, y: 10 },
        visible: { opacity: 1, y: 0 },
      }}
      transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
    >
      <span aria-hidden="true" className={`absolute inset-x-0 top-0 h-0.5 ${colors.topRule}`} />

      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-muted">{title}</p>
        <span
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${colors.icon}`}
          aria-hidden="true"
        >
          <Icon className="h-4 w-4" />
        </span>
      </div>

      <p
        className={`tnum mt-2 text-[1.75rem] font-semibold leading-8 ${colors.value} ${
          nowrapValue ? "truncate" : ""
        }`}
      >
        <CountUpValue value={value} />
      </p>

      <div className="mt-auto flex items-end justify-between gap-2 pt-3">
        <p className="min-w-0 text-xs font-medium leading-4 text-ink-muted">{detail}</p>
        <span className="shrink-0 rounded-full border border-hairline px-2 py-0.5 text-[10px] font-medium text-ink-muted">
          {status}
        </span>
      </div>
    </motion.section>
  );
}
