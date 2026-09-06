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
      className={`grid gap-3 rounded-xl border bg-surface p-4 shadow-card md:grid-cols-[minmax(180px,0.7fr)_minmax(260px,1.3fr)_auto] md:items-center ${
        selectedFile ? "border-anchor/40 ring-1 ring-anchor/15" : "border-hairline"
      }`}
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      onSubmit={handleSubmit}
    >
      <div className="flex min-w-0 items-center gap-3">
        <span
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-anchor-weak text-anchor"
          aria-hidden="true"
        >
          <FileSpreadsheet className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">Fichier de transactions</p>
          <p className="truncate text-xs text-ink-muted">
            {datasetPath ? "Dataset analysé" : "CSV, JSON, JSONL ou Parquet"}
          </p>
          <AnimatePresence mode="wait">
            {selectedFile ? (
              <motion.p
                className="mt-1 truncate text-xs font-semibold text-anchor"
                title={selectedFile.name}
                initial={{ opacity: 0, y: 3 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -3 }}
                transition={{ duration: 0.18 }}
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
          className="block w-full rounded-lg border border-hairline bg-canvas px-2 py-1.5 text-sm text-ink-muted file:mr-3 file:rounded-md file:border-0 file:bg-surface file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-anchor hover:file:bg-anchor-weak"
          type="file"
          onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
        />
      </label>

      <motion.button
        className="inline-flex min-h-10 items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-anchor px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-anchor-strong disabled:cursor-not-allowed disabled:bg-ink-faint"
        type="submit"
        disabled={loading || !selectedFile}
        whileTap={!loading && selectedFile ? { scale: 0.98 } : undefined}
        title={loading ? "Analyse en cours…" : "Téléverser et analyser"}
      >
        <motion.span
          animate={loading ? { rotate: 360 } : { rotate: 0 }}
          transition={loading ? { duration: 0.9, repeat: Infinity, ease: "linear" } : { duration: 0.18 }}
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
        </motion.span>
        {loading ? "Analyse en cours…" : "Téléverser et analyser"}
      </motion.button>
    </motion.form>
  );
}
