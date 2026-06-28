import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Eye, RotateCcw, SlidersHorizontal, X } from "lucide-react";
import type { ModelPredictionResult, PredictionPreview } from "../api/client";

type AnomalyRow = PredictionPreview & {
  model: "ensemble";
};

type AnomaliesViewProps = {
  results: ModelPredictionResult[];
};

const PAGE_SIZE = 100;

function uniqueValues(rows: AnomalyRow[], key: keyof AnomalyRow) {
  return [...new Set(rows.map((row) => String(row[key] ?? "")).filter(Boolean))].sort();
}

function formatAmount(value?: number) {
  return `${new Intl.NumberFormat("fr-FR").format(Number(value ?? 0))} MRU`;
}

function formatDate(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function readableLabel(value?: string) {
  if (!value) return "None";
  return value.replace(/_/g, " ").toLowerCase().replace(/^\w/, (letter: string) => letter.toUpperCase());
}

function anomalyTone(value?: string) {
  const label = value?.toUpperCase() ?? "";
  if (label.includes("HIGH")) return "bg-rose-50 text-rose-700 ring-rose-100";
  if (label.includes("OUTAGE")) return "bg-orange-50 text-orange-700 ring-orange-100";
  if (label.includes("LOCATION")) return "bg-violet-50 text-violet-700 ring-violet-100";
  return "bg-slate-100 text-slate-600 ring-slate-200";
}

function statusTone(value?: string) {
  return value?.toUpperCase() === "SUCCESS"
    ? "bg-emerald-50 text-emerald-700 ring-emerald-100"
    : "bg-rose-50 text-rose-700 ring-rose-100";
}

function splitBusinessReasons(value?: string) {
  if (!value) return [];
  return value
    .split(/[|;,]/)
    .map((reason) => reason.trim())
    .filter(Boolean);
}

function explainAnomaly(row: AnomalyRow) {
  const type = row.anomaly_type?.toUpperCase() ?? "";
  const operator = row.operator ?? "cet operateur";
  const wilaya = row.sender_wilaya ?? row.receiver_wilaya ?? "cette wilaya";
  const amount = formatAmount(row.amount);
  const status = row.status?.toUpperCase() ?? "";
  const score = Number(row.anomaly_score ?? 0).toFixed(3);
  const businessReasons = splitBusinessReasons(row.business_rule_reasons);

  if (type.includes("HIGH")) {
    return {
      title: "Montant inhabituellement eleve",
      summary: `Cette transaction est signalee parce que son montant (${amount}) est tres eleve par rapport au comportement attendu dans le dataset.`,
      factors: [
        "Le montant est un signal important pour la detection.",
        `La transaction concerne ${operator} dans ${wilaya}.`,
        `Score d'anomalie calcule: ${score}.`,
        status === "SUCCESS"
          ? "Le paiement a reussi, donc il peut representer un risque financier reel."
          : "Le paiement a echoue, mais la tentative reste importante pour l'analyse du risque.",
      ],
      businessReasons,
    };
  }

  if (type.includes("OUTAGE")) {
    return {
      title: "Suspicion de probleme operateur",
      summary: `Cette transaction est signalee car elle ressemble a un incident ou une interruption de service chez ${operator}.`,
      factors: [
        status === "FAILED"
          ? "Le statut FAILED renforce l'hypothese d'un probleme technique ou d'une panne temporaire."
          : "Même si le statut n'est pas FAILED, le contexte operateur reste anormal.",
        `Zone observee: ${wilaya}.`,
        `Montant observe: ${amount}.`,
        `Score d'anomalie calcule: ${score}.`,
      ],
      businessReasons,
    };
  }

  if (type.includes("LOCATION")) {
    return {
      title: "Localisation inhabituelle",
      summary: `Cette transaction est detectee car sa localisation (${wilaya}) parait inhabituelle par rapport aux habitudes observees.`,
      factors: [
        "La wilaya ou le chemin de transaction sort du comportement attendu.",
        `Operateur concerne: ${operator}.`,
        `Montant observe: ${amount}.`,
        `Score d'anomalie calcule: ${score}.`,
      ],
      businessReasons,
    };
  }

  return {
    title: "Transaction consideree comme atypique",
    summary: "Cette transaction est signalee par le consensus de detection car plusieurs signaux statistiques ou metier la rendent differente des transactions normales.",
    factors: [
      `Type detecte: ${readableLabel(row.anomaly_type)}.`,
      `Operateur concerne: ${operator}.`,
      `Zone observee: ${wilaya}.`,
      `Score d'anomalie calcule: ${score}.`,
    ],
    businessReasons,
  };
}

export function AnomaliesView({ results }: AnomaliesViewProps) {
  const [wilaya, setWilaya] = useState("");
  const [operator, setOperator] = useState("");
  const [anomalyType, setAnomalyType] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<AnomalyRow | null>(null);

  const rows = useMemo<AnomalyRow[]>(
    () => {
      const ensemble = results.find((result) => result.algorithm === "ensemble");
      return (ensemble?.preview ?? []).map((transaction) => ({
        ...transaction,
        model: "ensemble",
      }));
    },
    [results],
  );

  const filteredRows = useMemo(
    () =>
      rows.filter((row) => {
        const rowWilaya = row.sender_wilaya ?? row.receiver_wilaya ?? "";
        return (
          (!wilaya || rowWilaya === wilaya)
          && (!operator || row.operator === operator)
          && (!anomalyType || row.anomaly_type === anomalyType)
        );
      }),
    [anomalyType, operator, rows, wilaya],
  );
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const startIndex = (currentPage - 1) * PAGE_SIZE;
  const endIndex = Math.min(startIndex + PAGE_SIZE, filteredRows.length);
  const paginatedRows = useMemo(
    () => filteredRows.slice(startIndex, endIndex),
    [endIndex, filteredRows, startIndex],
  );
  const wilayas = useMemo(
    () => [...new Set(rows.map((row) => row.sender_wilaya ?? row.receiver_wilaya ?? "").filter(Boolean))].sort(),
    [rows],
  );
  const anomalyTypes = useMemo(
    () => uniqueValues(rows, "anomaly_type"),
    [rows],
  );
  const hasFilters = Boolean(wilaya || operator || anomalyType);

  useEffect(() => {
    setPage(1);
  }, [anomalyType, operator, results, wilaya]);

  function resetFilters() {
    setWilaya("");
    setOperator("");
    setAnomalyType("");
    setPage(1);
  }

  if (results.length === 0) {
    return (
      <section className="dashboard-card p-6 text-sm font-medium text-slate-500">
        Televersez un fichier pour afficher les transactions suspectes.
      </section>
    );
  }

  return (
    <section className="space-y-4" aria-label="Vue anomalies">
      <motion.div
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="dashboard-card border-emerald-100 bg-white p-4 shadow-[0_16px_38px_-28px_rgba(15,23,42,0.45)]"
        initial={{ opacity: 0, y: -14, scale: 0.99 }}
        transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
        whileHover={{ boxShadow: "0 18px 38px -28px rgba(5, 99, 76, 0.4)" }}
      >
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm font-extrabold text-ink">
            <span className="flex h-8 w-8 items-center justify-center rounded bg-emerald-50 text-mauri-green">
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
            </span>
            Filtres
          </div>
          <motion.button
            className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-xs font-extrabold text-slate-500 shadow-sm transition hover:-translate-y-0.5 hover:border-mauri-green hover:text-mauri-green hover:shadow-md disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
            disabled={!hasFilters}
            onClick={resetFilters}
            type="button"
            whileHover={hasFilters ? { y: -2, scale: 1.02 } : undefined}
            whileTap={hasFilters ? { scale: 0.97 } : undefined}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Reinitialiser
          </motion.button>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <motion.label
            animate={{ opacity: 1, x: 0 }}
            className="text-xs font-extrabold text-slate-600"
            initial={{ opacity: 0, x: -10 }}
            transition={{ delay: 0.16, duration: 0.32 }}
          >
            Wilaya
            <select
              aria-label="Filtrer par wilaya"
              className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-ink outline-none transition hover:border-slate-400 focus:border-mauri-green focus:ring-2 focus:ring-emerald-100"
              onChange={(event) => setWilaya(event.target.value)}
              value={wilaya}
            >
              <option value="">Toutes</option>
              {wilayas.map((value) => <option key={value}>{value}</option>)}
            </select>
          </motion.label>

          <motion.label
            animate={{ opacity: 1, x: 0 }}
            className="text-xs font-extrabold text-slate-600"
            initial={{ opacity: 0, x: 10 }}
            transition={{ delay: 0.22, duration: 0.32 }}
          >
            Operateur
            <select
              aria-label="Filtrer par opérateur"
              className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-ink outline-none transition hover:border-slate-400 focus:border-mauri-green focus:ring-2 focus:ring-emerald-100"
              onChange={(event) => setOperator(event.target.value)}
              value={operator}
            >
              <option value="">Tous</option>
              {uniqueValues(rows, "operator").map((value) => <option key={value}>{value}</option>)}
            </select>
          </motion.label>

          <motion.label
            animate={{ opacity: 1, x: 0 }}
            className="text-xs font-extrabold text-slate-600"
            initial={{ opacity: 0, x: 10 }}
            transition={{ delay: 0.28, duration: 0.32 }}
          >
            Type d'anomalie
            <select
              aria-label="Filtrer par type d'anomalie"
              className="mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-ink outline-none transition hover:border-slate-400 focus:border-mauri-green focus:ring-2 focus:ring-emerald-100"
              onChange={(event) => setAnomalyType(event.target.value)}
              value={anomalyType}
            >
              <option value="">Tous</option>
              {anomalyTypes.map((value) => (
                <option key={value} value={value}>{readableLabel(value)}</option>
              ))}
            </select>
          </motion.label>
        </div>
      </motion.div>

      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="dashboard-card overflow-hidden border-slate-200 bg-white shadow-[0_18px_42px_-30px_rgba(15,23,42,0.45)]"
        initial={{ opacity: 0, y: 18 }}
        transition={{ delay: 0.12, duration: 0.48, ease: [0.22, 1, 0.36, 1] }}
        whileHover={{ boxShadow: "0 20px 44px -30px rgba(15, 23, 42, 0.52)" }}
      >
        <div className="soft-scrollbar max-h-[560px] overflow-auto">
          <table className="w-full min-w-[1240px] table-fixed text-left text-sm">
            <thead className="sticky top-0 z-10 bg-slate-50/95 text-[11px] uppercase tracking-wide text-slate-500 shadow-[0_1px_0_rgba(148,163,184,0.28)]">
              <tr>
                <th className="w-[9.5rem] px-4 py-3 font-extrabold">Date</th>
                <th className="w-[17rem] px-4 py-3 font-extrabold">Transaction</th>
                <th className="w-24 px-4 py-3 font-extrabold">Score</th>
                <th className="w-40 px-4 py-3 font-extrabold">Type</th>
                <th className="w-40 px-4 py-3 font-extrabold">Wilaya</th>
                <th className="w-32 px-4 py-3 font-extrabold">Operateur</th>
                <th className="w-36 px-4 py-3 font-extrabold">Montant</th>
                <th className="w-28 px-4 py-3 font-extrabold">Statut</th>
                <th className="w-20 px-4 py-3 text-center font-extrabold">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedRows.map((row, index) => {
                const wilayaName = row.sender_wilaya ?? row.receiver_wilaya ?? "-";

                return (
                  <motion.tr
                    animate={{ opacity: 1, x: 0 }}
                    className="text-slate-700 transition-colors hover:bg-emerald-50/45"
                    initial={{ opacity: 0, x: 8 }}
                    key={`${row.model}-${row.transaction_id ?? startIndex + index}`}
                    transition={{ delay: 0.2 + Math.min(index * 0.012, 0.25), duration: 0.24 }}
                  >
                    <td className="whitespace-nowrap px-4 py-3.5 text-xs font-semibold text-slate-600">
                      {formatDate(row.timestamp)}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="block max-w-[15rem] truncate font-mono text-xs font-semibold text-slate-700" title={row.transaction_id ?? "-"}>
                        {row.transaction_id ?? "-"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs font-extrabold text-slate-700">
                      {Number(row.anomaly_score ?? 0).toFixed(3)}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-extrabold ring-1 ${anomalyTone(row.anomaly_type)}`}>
                        {readableLabel(row.anomaly_type)}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="block max-w-[9rem] whitespace-normal leading-5" title={wilayaName}>
                        {wilayaName}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="block truncate" title={row.operator ?? "-"}>
                        {row.operator ?? "-"}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 font-extrabold text-slate-700">
                      {formatAmount(row.amount)}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-extrabold ring-1 ${statusTone(row.status)}`}>
                        {row.status ?? "-"}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      <motion.button
                        aria-label={`Voir ${row.transaction_id ?? "la transaction"}`}
                        className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-100 bg-white text-mauri-green shadow-sm transition hover:-translate-y-0.5 hover:border-mauri-green hover:bg-emerald-50 hover:shadow-md"
                        onClick={() => setSelected(row)}
                        type="button"
                        whileHover={{ y: -2, scale: 1.08 }}
                        whileTap={{ scale: 0.92 }}
                      >
                        <Eye className="h-4 w-4" />
                      </motion.button>
                    </td>
                  </motion.tr>
                );
              })}
              {filteredRows.length === 0 ? (
                <tr>
                  <td className="px-4 py-10 text-center text-sm text-slate-500" colSpan={9}>
                    Aucune transaction ne correspond aux filtres selectionnes.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </motion.div>

      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="dashboard-card flex flex-col gap-3 px-3 py-3 text-sm sm:flex-row sm:items-center sm:justify-between"
        initial={{ opacity: 0, y: 10 }}
        transition={{ delay: 0.28, duration: 0.35 }}
      >
        <div className="text-xs font-medium text-slate-500">
          {filteredRows.length > 0
            ? `${(startIndex + 1).toLocaleString("fr-FR")} - ${endIndex.toLocaleString("fr-FR")} sur ${filteredRows.length.toLocaleString("fr-FR")} anomalies`
            : "0 anomalie"}
        </div>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex items-center gap-1.5 rounded border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm transition hover:border-mauri-green hover:text-mauri-green disabled:cursor-not-allowed disabled:opacity-40"
            disabled={currentPage <= 1}
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            type="button"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Precedent
          </button>
          <span className="min-w-24 text-center text-xs font-semibold text-slate-600">
            Page {currentPage.toLocaleString("fr-FR")} / {pageCount.toLocaleString("fr-FR")}
          </span>
          <button
            className="inline-flex items-center gap-1.5 rounded border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm transition hover:border-mauri-green hover:text-mauri-green disabled:cursor-not-allowed disabled:opacity-40"
            disabled={currentPage >= pageCount}
            onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
            type="button"
          >
            Suivant
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </motion.div>

      {selected ? (() => {
        const explanation = explainAnomaly(selected);

        return (
          <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-slate-950/50 p-4" role="dialog">
            <div className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-2xl bg-white shadow-[0_28px_80px_-35px_rgba(15,23,42,0.75)]">
              <header className="flex items-start justify-between gap-4 border-b border-slate-200 bg-slate-50/80 p-5">
                <div>
                  <p className="text-xs font-extrabold uppercase tracking-wide text-slate-500">Details de detection</p>
                  <h3 className="mt-1 text-lg font-black text-ink">{explanation.title}</h3>
                  <p className="mt-1 max-w-2xl text-sm font-medium text-slate-500">
                    Transaction {selected.transaction_id ?? "-"}
                  </p>
                </div>
                <button
                  aria-label="Fermer les details"
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600"
                  onClick={() => setSelected(null)}
                  type="button"
                >
                  <X className="h-5 w-5" />
                </button>
              </header>

              <div className="space-y-4 p-5">
                <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-4">
                  <p className="text-xs font-extrabold uppercase tracking-wide text-mauri-green">
                    Pourquoi cette transaction est suspecte
                  </p>
                  <p className="mt-2 text-sm font-semibold leading-6 text-slate-700">{explanation.summary}</p>
                </div>

                <div className="grid gap-3 md:grid-cols-4">
                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="text-[11px] font-extrabold uppercase text-slate-400">Type</p>
                    <span className={`mt-2 inline-flex rounded-lg px-2.5 py-1 text-xs font-extrabold ring-1 ${anomalyTone(selected.anomaly_type)}`}>
                      {readableLabel(selected.anomaly_type)}
                    </span>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="text-[11px] font-extrabold uppercase text-slate-400">Score</p>
                    <p className="mt-2 font-mono text-sm font-black text-slate-700">
                      {Number(selected.anomaly_score ?? 0).toFixed(3)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="text-[11px] font-extrabold uppercase text-slate-400">Montant</p>
                    <p className="mt-2 text-sm font-black text-slate-700">{formatAmount(selected.amount)}</p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="text-[11px] font-extrabold uppercase text-slate-400">Statut</p>
                    <span className={`mt-2 inline-flex rounded-lg px-2.5 py-1 text-xs font-extrabold ring-1 ${statusTone(selected.status)}`}>
                      {selected.status ?? "-"}
                    </span>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                  <section className="rounded-2xl border border-slate-200 bg-white p-4">
                    <h4 className="text-sm font-black text-ink">Facteurs qui expliquent la detection</h4>
                    <ul className="mt-3 space-y-2">
                      {explanation.factors.map((factor) => (
                        <li className="flex gap-2 text-sm font-medium leading-6 text-slate-600" key={factor}>
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-mauri-green" />
                          <span>{factor}</span>
                        </li>
                      ))}
                    </ul>
                  </section>

                  <section className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                    <h4 className="text-sm font-black text-ink">Contexte transaction</h4>
                    <dl className="mt-3 space-y-3 text-sm">
                      <div>
                        <dt className="text-xs font-extrabold uppercase text-slate-400">Date</dt>
                        <dd className="mt-1 font-semibold text-slate-700">{formatDate(selected.timestamp)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs font-extrabold uppercase text-slate-400">Wilaya</dt>
                        <dd className="mt-1 font-semibold text-slate-700">
                          {selected.sender_wilaya ?? selected.receiver_wilaya ?? "-"}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs font-extrabold uppercase text-slate-400">Operateur</dt>
                        <dd className="mt-1 font-semibold text-slate-700">{selected.operator ?? "-"}</dd>
                      </div>
                    </dl>
                  </section>
                </div>

                {explanation.businessReasons.length > 0 ? (
                  <section className="rounded-2xl border border-orange-100 bg-orange-50/70 p-4">
                    <h4 className="text-sm font-black text-orange-800">Regles metier declenchees</h4>
                    <ul className="mt-3 space-y-2">
                      {explanation.businessReasons.map((reason) => (
                        <li className="flex gap-2 text-sm font-semibold leading-6 text-orange-800" key={reason}>
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-500" />
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </section>
                ) : null}

                <details className="rounded-2xl border border-slate-200 bg-white p-4">
                  <summary className="cursor-pointer text-sm font-black text-ink">Donnees techniques completes</summary>
                  <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                    {Object.entries(selected).map(([key, value]) => (
                      <div className="rounded bg-slate-50 p-3" key={key}>
                        <dt className="text-xs uppercase text-slate-500">{key}</dt>
                        <dd className="mt-1 break-words text-sm text-slate-800">{String(value ?? "-")}</dd>
                      </div>
                    ))}
                  </dl>
                </details>
              </div>
            </div>
          </div>
        );
      })() : null}    </section>
  );
}

