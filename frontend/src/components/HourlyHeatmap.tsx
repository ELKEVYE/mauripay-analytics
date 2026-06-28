import { Clock3 } from "lucide-react";
import { motion } from "framer-motion";

type HeatmapRow = {
  day_of_week: string;
  hour: number;
  transactions: number;
};

type HourlyHeatmapProps = {
  rows: HeatmapRow[];
  compact?: boolean;
};

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const DAY_LABELS: Record<string, string> = {
  Monday: "Lun",
  Tuesday: "Mar",
  Wednesday: "Mer",
  Thursday: "Jeu",
  Friday: "Ven",
  Saturday: "Sam",
  Sunday: "Dim",
};

export function HourlyHeatmap({ rows, compact = false }: HourlyHeatmapProps) {
  const max = Math.max(...rows.map((row) => row.transactions), 1);
  const valueBySlot = new Map(
    rows.map((row) => [`${row.day_of_week}-${row.hour}`, row.transactions]),
  );

  return (
    <motion.section
      className={`dashboard-card chart-card flex flex-col border-emerald-100 bg-gradient-to-br from-white via-white to-emerald-50/45 ${
        compact ? "min-h-[360px] lg:min-h-0" : "p-4"
      }`}
      initial={{ opacity: 0, y: 22, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      whileHover={{
        y: -5,
        boxShadow: "0 24px 55px -34px rgba(15, 23, 42, 0.45)",
      }}
      transition={{ duration: 0.46, ease: "easeOut" }}
    >
      <header className="mb-3 flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-emerald-50 text-mauri-green">
          <Clock3 className="h-[18px] w-[18px]" aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-sm font-extrabold text-ink">Heatmap horaire</h2>
          <p className="mt-0.5 text-xs font-medium text-slate-500">Activite par jour et par heure</p>
        </div>
      </header>
      <div className="soft-scrollbar min-h-0 flex-1 overflow-x-auto rounded bg-white/70 p-2">
        <div
          className={`grid min-w-[760px] gap-1.5 ${compact ? "xl:min-w-0" : ""}`}
          style={{ gridTemplateColumns: "44px repeat(24, minmax(14px, 1fr))" }}
        >
          <div />
          {Array.from({ length: 24 }, (_, hour) => (
            <div className="self-center text-center text-[10px] font-bold text-slate-500" key={hour}>
              {hour}
            </div>
          ))}
          {DAYS.map((day) => (
            <div className="contents" key={day}>
              <div className="flex items-center text-xs font-bold text-slate-600">{DAY_LABELS[day]}</div>
              {Array.from({ length: 24 }, (_, hour) => {
                const value = valueBySlot.get(`${day}-${hour}`) ?? 0;
                const opacity = 0.1 + (value / max) * 0.82;
                return (
                  <motion.div
                    className="h-5 rounded border border-white shadow-sm transition hover:scale-110 hover:ring-2 hover:ring-emerald-200"
                    initial={{ opacity: 0, scale: 0.82 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{
                      delay: 0.08 + DAYS.indexOf(day) * 0.035 + hour * 0.006,
                      duration: 0.22,
                      ease: "easeOut",
                    }}
                    whileHover={{ scale: 1.18, zIndex: 2 }}
                    key={`${day}-${hour}`}
                    style={{ backgroundColor: `rgba(31, 122, 91, ${opacity})` }}
                    title={`${DAY_LABELS[day]} ${hour}h: ${value.toLocaleString("fr-FR")} transactions`}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-end gap-2 text-[11px] font-bold text-slate-500">
        <span>Faible</span>
        <span className="h-2 w-12 rounded-full bg-gradient-to-r from-emerald-100 to-mauri-green" />
        <span>Fort</span>
      </div>
    </motion.section>
  );
}
