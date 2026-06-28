import { useEffect, useMemo, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";

type StatCardProps = {
  title: string;
  value: string;
  detail: string;
  status: string;
  icon: LucideIcon;
  tone?: "green" | "gold" | "red" | "blue";
  nowrapValue?: boolean;
};

const toneClasses = {
  green: {
    card:
      "border-emerald-500/50 bg-[radial-gradient(circle_at_90%_95%,rgba(255,255,255,0.18),transparent_28%),linear-gradient(135deg,#059669_0%,#047857_52%,#064e3b_100%)] shadow-[0_14px_30px_-22px_rgba(4,120,87,0.72)]",
    icon: "bg-white/16 text-emerald-50 ring-1 ring-inset ring-white/30 shadow-sm",
    badge: "bg-white/14 text-emerald-50 ring-white/20",
  },
  gold: {
    card:
      "border-amber-400/60 bg-[radial-gradient(circle_at_92%_92%,rgba(255,255,255,0.18),transparent_30%),linear-gradient(135deg,#f59e0b_0%,#f97316_55%,#b45309_100%)] shadow-[0_14px_30px_-22px_rgba(217,119,6,0.68)]",
    icon: "bg-white/20 text-white ring-1 ring-inset ring-white/25 shadow-sm",
    badge: "bg-white/16 text-amber-50 ring-white/22",
  },
  red: {
    card:
      "border-rose-500/60 bg-[radial-gradient(circle_at_92%_95%,rgba(255,255,255,0.16),transparent_30%),linear-gradient(135deg,#e11d48_0%,#db2777_52%,#9f1239_100%)] shadow-[0_14px_30px_-22px_rgba(225,29,72,0.68)]",
    icon: "bg-white/15 text-rose-50 ring-1 ring-inset ring-white/25 shadow-sm",
    badge: "bg-white/14 text-rose-50 ring-white/20",
  },
  blue: {
    card:
      "border-blue-500/60 bg-[radial-gradient(circle_at_92%_95%,rgba(255,255,255,0.17),transparent_30%),linear-gradient(135deg,#3b82f6_0%,#2563eb_54%,#3730a3_100%)] shadow-[0_14px_30px_-22px_rgba(37,99,235,0.68)]",
    icon: "bg-white/15 text-blue-50 ring-1 ring-inset ring-white/25 shadow-sm",
    badge: "bg-white/14 text-blue-50 ring-white/20",
  },
};

function parseDisplayValue(value: string) {
  if (value === "—" || value.trim() === "") {
    return null;
  }

  const match = value.match(/[\d\s\u202f.,]+/);
  if (!match) return null;

  const rawNumber = match[0];
  const normalized = rawNumber.replace(/[\s\u202f]/g, "").replace(",", ".");
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
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    if (!parsed) {
      setDisplayValue(value);
      return;
    }

    const parsedValue = parsed;
    let frameId = 0;
    const duration = 620;
    const start = performance.now();
    const formatter = new Intl.NumberFormat("fr-FR", {
      maximumFractionDigits: parsedValue.decimals,
      minimumFractionDigits: parsedValue.decimals,
    });

    function tick(now: number) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = parsedValue.target * eased;
      const formatted = parsedValue.decimalSeparator === "."
        ? formatter.format(current).replace(",", ".")
        : formatter.format(current);
      setDisplayValue(`${parsedValue.prefix}${formatted}${parsedValue.suffix}`);

      if (progress < 1) {
        frameId = requestAnimationFrame(tick);
      }
    }

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [parsed, value]);

  return <>{displayValue}</>;
}

export function StatCard({
  title,
  value,
  detail,
  status,
  icon: Icon,
  tone = "green",
  nowrapValue = false,
}: StatCardProps) {
  const colors = toneClasses[tone];

  return (
    <motion.section
      className={`group relative flex min-h-[136px] flex-col overflow-hidden rounded-2xl border p-3.5 text-white ${colors.card}`}
      variants={{
        hidden: { opacity: 0, y: 20, scale: 0.98 },
        visible: { opacity: 1, y: 0, scale: 1 },
        hover: {
          y: -6,
          filter: "saturate(1.05)",
          boxShadow: "0 18px 35px rgba(15, 23, 42, 0.18)",
        },
      }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      whileHover="hover"
    >
      <motion.span
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 -left-1/2 w-1/2 skew-x-[-18deg] bg-white/18 blur-[2px]"
        variants={{
          visible: { x: "-120%", opacity: 0 },
          hover: { x: "360%", opacity: [0, 0.45, 0] },
        }}
        transition={{ duration: 0.75, ease: "easeOut" }}
      />
      <motion.div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-8 -right-6 text-white/10 group-hover:text-white/14"
        animate={{ x: [0, -4, 0], y: [0, -5, 0], rotate: [0, -1.5, 0] }}
        transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut" }}
        variants={{
          hover: { scale: 1.04, opacity: 0.95 },
        }}
      >
        <Icon className="h-24 w-24" />
      </motion.div>
      <span className="pointer-events-none absolute inset-x-0 top-0 h-px bg-white/40" />
      <span className="pointer-events-none absolute inset-0 bg-white/[0.03] opacity-0 transition group-hover:opacity-100" />
      <div className="relative flex min-w-0 items-start justify-between gap-2.5">
        <div className="min-w-0 flex-1">
          <p className="pr-1 text-xs font-extrabold leading-4 text-white/90">{title}</p>
          <p
            className={`mt-1.5 text-[clamp(1.22rem,1.8vw,1.55rem)] font-black leading-7 text-white ${
              nowrapValue ? "whitespace-nowrap" : "max-w-[13rem]"
            }`}
          >
            <CountUpValue value={value} />
          </p>
        </div>
        <span className={`shrink-0 rounded-xl p-2.5 backdrop-blur ${colors.icon}`} title={title}>
          <motion.span
            className="block"
            variants={{
              visible: { scale: 1, rotate: 0 },
              hover: { scale: 1.14, rotate: -2 },
            }}
            transition={{ duration: 0.22 }}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
          </motion.span>
        </span>
      </div>
      <div className="relative mt-auto flex min-w-0 items-end justify-between gap-2 pt-3">
        <p className="min-w-0 text-xs font-semibold leading-4 text-white/84">{detail}</p>
        <motion.span
          className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-extrabold ring-1 ${colors.badge}`}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: [0.95, 1, 1.018, 1] }}
          transition={{
            opacity: { delay: 0.46, duration: 0.28 },
            scale: { delay: 0.46, duration: 3.8, repeat: Infinity, repeatDelay: 2.6, ease: "easeInOut" },
          }}
        >
          {status}
        </motion.span>
      </div>
    </motion.section>
  );
}
