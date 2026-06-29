type StatusBadgeProps = {
  active: boolean;
  label: string;
};

export function StatusBadge({ active, label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-1 text-xs font-semibold ${
        active ? "bg-emerald-50 text-mauri-green" : "bg-slate-100 text-slate-500"
      }`}
    >
      {label}
    </span>
  );
}
