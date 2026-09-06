import { Table2 } from "lucide-react";
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
};

export function DataTable<T extends object>({
  title,
  rows,
  columns,
  emptyLabel = "Aucune donnée",
  compact = false,
}: DataTableProps<T>) {
  return (
    <section
      className={`dashboard-card overflow-hidden ${
        compact ? "flex min-h-[19rem] flex-col lg:min-h-0" : ""
      }`}
    >
      <header
        className={`flex shrink-0 items-center gap-3 border-b border-hairline ${
          compact ? "px-4 py-3" : "px-4 py-3.5"
        }`}
      >
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-anchor-weak text-anchor"
          aria-hidden="true"
        >
          <Table2 className="h-4 w-4" />
        </span>
        <h2 className={`${compact ? "text-sm" : "text-[15px]"} font-semibold text-ink`}>{title}</h2>
      </header>
      <div className={`soft-scrollbar ${compact ? "min-h-0 flex-1 overflow-auto" : "overflow-x-auto"}`}>
        <table className="min-w-full text-left text-[13px]">
          <thead
            className={`bg-canvas text-[11px] uppercase tracking-[0.04em] text-ink-muted ${
              compact ? "sticky top-0 z-10" : ""
            }`}
          >
            <tr>
              {columns.map((column) => (
                <th
                  className={`${compact ? "whitespace-nowrap px-4 py-2.5" : "px-4 py-2.5"} font-semibold`}
                  key={String(column.key)}
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-4 text-ink-muted" colSpan={columns.length}>
                  {emptyLabel}
                </td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <tr key={index} className="transition-colors hover:bg-anchor-weak/60">
                  {columns.map((column) => (
                    <td
                      className={`${
                        compact ? "whitespace-nowrap px-4 py-3" : "px-4 py-3"
                      } font-medium text-ink`}
                      key={String(column.key)}
                    >
                      {column.render ? column.render(row) : String(row[column.key] ?? "")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
