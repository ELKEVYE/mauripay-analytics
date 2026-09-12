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
      className={`dashboard-card chart-card flex flex-col ${compact ? "min-h-[360px] lg:min-h-0" : ""}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: "easeOut" }}
    >
      <header className="mb-3 flex items-start gap-3">
        <span
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-anchor-weak text-anchor"
          aria-hidden="true"
        >
          <Clock3 className="h-[18px] w-[18px]" />
        </span>
        <div>
          <h2 className="text-[13px] font-semibold text-ink">Heatmap horaire</h2>
          <p className="mt-0.5 text-xs text-ink-muted">Activité par jour et par heure</p>
        </div>
      </header>
      <div className="soft-scrollbar min-h-0 flex-1 overflow-x-auto">
        <div
          className={`grid min-w-[760px] gap-1 ${compact ? "xl:min-w-0" : ""}`}
          style={{ gridTemplateColumns: "40px repeat(24, minmax(14px, 1fr))" }}
        >
          <div />
          {Array.from({ length: 24 }, (_, hour) => (
            <div className="tnum self-center text-center text-[10px] font-medium text-ink-faint" key={hour}>
              {hour}
            </div>
          ))}
          {DAYS.map((day, dayIndex) => (
            <div className="contents" key={day}>
              <div className="flex items-center text-[11px] font-medium text-ink-muted">
                {DAY_LABELS[day]}
              </div>
              {Array.from({ length: 24 }, (_, hour) => {
                const value = valueBySlot.get(`${day}-${hour}`) ?? 0;
                const intensity = 0.06 + (value / max) * 0.9;
                return (
                  <motion.div
                    className="h-5 rounded-[3px] transition-shadow hover:ring-1 hover:ring-anchor/40"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{
                      delay: 0.05 + dayIndex * 0.03 + hour * 0.004,
                      duration: 0.2,
                      ease: "easeOut",
                    }}
                    key={`${day}-${hour}`}
                    style={{ backgroundColor: `rgba(12, 92, 76, ${intensity})` }}
                    title={`${DAY_LABELS[day]} ${hour}h — ${value.toLocaleString("fr-FR")} transactions`}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-end gap-2 text-[11px] font-medium text-ink-muted">
        <span>Faible</span>
        <span
          aria-hidden="true"
          className="h-2 w-16 rounded-full"
          style={{ background: "linear-gradient(90deg, rgba(12,92,76,0.10), rgba(12,92,76,0.95))" }}
        />
        <span>Fort</span>
      </div>
    </motion.section>
  );
}
