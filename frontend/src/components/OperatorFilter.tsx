import { RotateCcw, SlidersHorizontal } from "lucide-react";

type OperatorFilterProps = {
  operators: string[];
  value: string;
  onChange: (value: string) => void;
};

export function OperatorFilter({ operators, value, onChange }: OperatorFilterProps) {
  return (
    <div className="dashboard-card grid w-full gap-3 border-emerald-100 bg-white p-3 shadow-[0_18px_44px_rgba(15,118,110,0.12)] sm:grid-cols-[minmax(220px,1fr)_auto] sm:items-end lg:w-[380px]">
      <label className="block">
        <span className="flex items-center gap-2 text-xs font-extrabold text-slate-600">
          <SlidersHorizontal className="h-3.5 w-3.5 text-mauri-green" />
          Operateur
        </span>
        <select
          className="mt-1 h-10 w-full rounded border border-slate-300 bg-white px-3 text-sm font-semibold text-ink outline-none transition hover:border-slate-400 focus:border-mauri-green focus:ring-2 focus:ring-emerald-100"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">Tous</option>
          {operators.map((operator) => (
            <option key={operator} value={operator}>
              {operator}
            </option>
          ))}
        </select>
      </label>
      <button
        className="inline-flex h-10 items-center justify-center gap-2 rounded border border-slate-200 bg-white px-3 text-xs font-extrabold text-slate-600 shadow-sm transition hover:-translate-y-0.5 hover:border-mauri-green hover:text-mauri-green hover:shadow-md disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
        disabled={!value}
        onClick={() => onChange("")}
        type="button"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        Reinitialiser
      </button>
    </div>
  );
}
