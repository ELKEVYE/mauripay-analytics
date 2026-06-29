import { FileSpreadsheet, Upload } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import type { FormEvent } from "react";

type DatasetFilterProps = {
  datasetPath: string;
  loading: boolean;
  selectedFile: File | null;
  onFileChange: (file: File | null) => void;
  onSubmit: () => void;
};

export function DatasetFilter({
  datasetPath,
  loading,
  selectedFile,
  onFileChange,
  onSubmit,
}: DatasetFilterProps) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <motion.form
      className={`grid gap-3 rounded border bg-gradient-to-br from-white via-white to-emerald-50/35 p-4 shadow-[0_24px_56px_-26px_rgba(15,23,42,0.5),0_12px_26px_-20px_rgba(5,150,105,0.42)] md:grid-cols-[minmax(180px,0.7fr)_minmax(260px,1.3fr)_auto] md:items-center ${
        selectedFile ? "border-emerald-300/90 ring-2 ring-emerald-100/80" : "border-emerald-100/80"
      }`}
      initial={{ opacity: 0, y: -12 }}
      animate={{
        opacity: 1,
        y: 0,
        boxShadow: selectedFile
          ? [
              "0 24px 56px -26px rgba(15,23,42,0.5), 0 12px 26px -20px rgba(5,150,105,0.42)",
              "0 24px 56px -26px rgba(15,23,42,0.5), 0 0 0 4px rgba(16,185,129,0.14), 0 14px 30px -18px rgba(5,150,105,0.6)",
              "0 24px 56px -26px rgba(15,23,42,0.5), 0 12px 26px -20px rgba(5,150,105,0.42)",
            ]
          : "0 24px 56px -26px rgba(15,23,42,0.5), 0 12px 26px -20px rgba(5,150,105,0.42)",
      }}
      transition={{ duration: 0.42, ease: "easeOut" }}
      whileHover={{
        y: -2,
        boxShadow:
          "0 30px 66px -28px rgba(15,23,42,0.55), 0 16px 34px -22px rgba(5,150,105,0.5)",
      }}
      onSubmit={handleSubmit}
    >
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-emerald-50 text-mauri-green">
          <FileSpreadsheet className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-700">Fichier de transactions</p>
          <p className="truncate text-xs text-slate-400" title={datasetPath ? "Dataset analyse" : "Aucun dataset analyse"}>
            {datasetPath ? "Dataset analyse" : "CSV, JSON, JSONL ou Parquet"}
          </p>
          <AnimatePresence mode="wait">
            {selectedFile ? (
              <motion.p
                className="mt-1 truncate text-xs font-extrabold text-mauri-green"
                title={selectedFile.name}
                initial={{ opacity: 0, y: 4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -3, scale: 0.98 }}
                transition={{ duration: 0.22 }}
              >
                {selectedFile.name}
              </motion.p>
            ) : null}
          </AnimatePresence>
        </div>
      </div>

      <label className="min-w-0">
        <span className="sr-only">Choisir un fichier de transactions</span>
        <input
          accept=".csv,.json,.jsonl,.parquet"
          className="block w-full rounded border border-slate-300 bg-slate-50 px-2 py-1.5 text-sm text-slate-600 file:mr-3 file:rounded file:border-0 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-mauri-green hover:file:bg-emerald-50"
          type="file"
          onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
        />
      </label>

      <motion.button
        className="inline-flex min-h-10 items-center justify-center gap-2 whitespace-nowrap rounded bg-gradient-to-br from-emerald-600 to-emerald-800 px-4 py-2 text-sm font-semibold text-white shadow-[0_14px_28px_-16px_rgba(4,120,87,0.85)] disabled:cursor-not-allowed disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none"
        type="submit"
        disabled={loading || !selectedFile}
        whileHover={!loading && selectedFile ? { y: -2, boxShadow: "0 18px 34px -18px rgba(4,120,87,0.95)" } : undefined}
        whileTap={!loading && selectedFile ? { scale: 0.98 } : undefined}
        title={loading ? "Analyse en cours..." : "Téléverser et analyser"}
      >
        <motion.span
          animate={loading ? { rotate: 360 } : { rotate: 0 }}
          transition={loading ? { duration: 0.9, repeat: Infinity, ease: "linear" } : { duration: 0.18 }}
          whileHover={!loading && selectedFile ? { x: 2, y: -1 } : undefined}
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
        </motion.span>
        {loading ? "Analyse en cours..." : "Téléverser et analyser"}
      </motion.button>
    </motion.form>
  );
}
