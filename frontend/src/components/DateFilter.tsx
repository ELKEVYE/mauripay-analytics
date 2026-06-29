import { CalendarDays, RotateCcw } from "lucide-react";

type DateFilterProps = {
  startDate: string;
  endDate: string;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;
};

export function DateFilter({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
}: DateFilterProps) {
  const hasDates = Boolean(startDate || endDate);

  return (
    <div className="dashboard-card grid gap-3 p-3 sm:grid-cols-[minmax(150px,1fr)_minmax(150px,1fr)_auto] sm:items-end lg:w-[500px]">
      <label className="grid grid-cols-[auto_1fr] items-center gap-2 sm:block">
        <span className="whitespace-nowrap text-xs font-semibold text-slate-500">Date debut</span>
        <input
          className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition hover:border-slate-400 focus:border-mauri-green focus:ring-2 focus:ring-emerald-100 sm:mt-1"
          type="date"
          value={startDate}
          onChange={(event) => onStartDateChange(event.target.value)}
        />
      </label>
      <label className="grid grid-cols-[auto_1fr] items-center gap-2 sm:block">
        <span className="whitespace-nowrap text-xs font-semibold text-slate-500">Date fin</span>
        <input
          className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition hover:border-slate-400 focus:border-mauri-green focus:ring-2 focus:ring-emerald-100 sm:mt-1"
          type="date"
          value={endDate}
          onChange={(event) => onEndDateChange(event.target.value)}
        />
      </label>
      <button
        className="inline-flex h-10 items-center justify-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600 shadow-sm transition hover:-translate-y-0.5 hover:border-mauri-green hover:text-mauri-green hover:shadow-md disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
        disabled={!hasDates}
        onClick={() => {
          onStartDateChange("");
          onEndDateChange("");
        }}
        type="button"
      >
        {hasDates ? <RotateCcw className="h-3.5 w-3.5" /> : <CalendarDays className="h-3.5 w-3.5" />}
        Reinitialiser
      </button>
    </div>
  );
}
