import { Table2 } from "lucide-react";
import { motion } from "framer-motion";
import type { ReactNode } from "react";

type Column<T> = {
  key: keyof T;
  label: string;
  render?: (row: T) => ReactNode;
};

type DataTableProps<T> = {
  title: string;
  rows: T[];
  columns: Array<Column<T>>;
  emptyLabel?: string;
  compact?: boolean;
  tone?: "default" | "green" | "blue" | "violet";
};

export function DataTable<T extends object>({
  title,
  rows,
  columns,
  emptyLabel = "Aucune donnée",
  compact = false,
  tone = "default",
}: DataTableProps<T>) {
  const toneClass = {
    default: "dashboard-card",
    green:
      "dashboard-card border-emerald-100 bg-gradient-to-br from-white via-white to-emerald-50/45",
    blue:
      "dashboard-card border-blue-100 bg-gradient-to-br from-white via-white to-blue-50/45",
    violet:
      "dashboard-card border-violet-100 bg-gradient-to-br from-white via-white to-violet-50/45",
  }[tone];

  return (
    <section
      className={`overflow-hidden ${toneClass} ${
        compact ? "flex min-h-[19rem] flex-col overflow-hidden lg:min-h-0" : ""
      }`}
    >
      <header className={`flex shrink-0 items-center gap-3 border-b border-slate-200/80 bg-white/70 ${compact ? "px-4 py-3" : "px-4 py-3.5"}`}>
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-emerald-50 text-mauri-green">
          <Table2 className="h-4 w-4" aria-hidden="true" />
        </span>
        <h2 className={`${compact ? "text-sm" : "text-base"} font-extrabold text-ink`}>{title}</h2>
      </header>
      <div className={`soft-scrollbar ${compact ? "min-h-0 flex-1 overflow-auto" : "overflow-x-auto"}`}>
        <table className="min-w-full text-left text-sm">
          <thead className={`bg-slate-50/95 text-[11px] uppercase tracking-wide text-slate-500 shadow-[0_1px_0_rgba(148,163,184,0.25)] ${compact ? "sticky top-0 z-10" : ""}`}>
            <tr>
              {columns.map((column) => (
                <th
                  className={`${compact ? "whitespace-nowrap px-4 py-3" : "px-4 py-3"} font-extrabold`}
                  key={String(column.key)}
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-4 text-slate-500" colSpan={columns.length}>
                  {emptyLabel}
                </td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <motion.tr
                  animate={{ opacity: 1, x: 0 }}
                  key={index}
                  className={`transition-colors hover:bg-emerald-50/55 ${
                    index === 0 ? "bg-emerald-50/25" : "bg-white/35"
                  }`}
                  initial={{ opacity: 0, x: 10 }}
                  transition={{ delay: Math.min(index * 0.045, 0.36), duration: 0.28, ease: "easeOut" }}
                >
                  {columns.map((column) => (
                    <td
                      className={`${compact ? "whitespace-nowrap px-4 py-3" : "px-4 py-3"} font-medium text-slate-700`}
                      key={String(column.key)}
                    >
                      {column.render ? column.render(row) : String(row[column.key] ?? "")}
                    </td>
                  ))}
                </motion.tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
