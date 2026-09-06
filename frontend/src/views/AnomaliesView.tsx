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

const typeBadge = "bg-alert-weak text-alert ring-1 ring-alert/20";

function statusBadge(value?: string) {
  return value?.toUpperCase() === "SUCCESS"
    ? "border border-hairline text-ink-muted"
    : "bg-alert-weak text-alert";
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
  const operator = row.operator ?? "cet opérateur";
  const wilaya = row.sender_wilaya ?? row.receiver_wilaya ?? "cette wilaya";
  const amount = formatAmount(row.amount);
  const status = row.status?.toUpperCase() ?? "";
  const score = Number(row.anomaly_score ?? 0).toFixed(3);
  const businessReasons = splitBusinessReasons(row.business_rule_reasons);

  if (type.includes("HIGH")) {
    return {
      title: "Montant inhabituellement élevé",
      summary: `Cette transaction est signalée parce que son montant (${amount}) est très élevé par rapport au comportement attendu dans le dataset.`,
      factors: [
        "Le montant est un signal important pour la détection.",
        `La transaction concerne ${operator} dans ${wilaya}.`,
        `Score d'anomalie calculé : ${score}.`,
        status === "SUCCESS"
          ? "Le paiement a réussi, il peut donc représenter un risque financier réel."
          : "Le paiement a échoué, mais la tentative reste importante pour l'analyse du risque.",
      ],
      businessReasons,
    };
  }

  if (type.includes("OUTAGE")) {
    return {
      title: "Suspicion de problème opérateur",
      summary: `Cette transaction est signalée car elle ressemble à un incident ou une interruption de service chez ${operator}.`,
      factors: [
        status === "FAILED"
          ? "Le statut FAILED renforce l'hypothèse d'un problème technique ou d'une panne temporaire."
          : "Même si le statut n'est pas FAILED, le contexte opérateur reste anormal.",
        `Zone observée : ${wilaya}.`,
        `Montant observé : ${amount}.`,
        `Score d'anomalie calculé : ${score}.`,
      ],
      businessReasons,
    };
  }

  if (type.includes("LOCATION")) {
    return {
      title: "Localisation inhabituelle",
      summary: `Cette transaction est détectée car sa localisation (${wilaya}) paraît inhabituelle par rapport aux habitudes observées.`,
      factors: [
        "La wilaya ou le chemin de transaction sort du comportement attendu.",
        `Opérateur concerné : ${operator}.`,
        `Montant observé : ${amount}.`,
        `Score d'anomalie calculé : ${score}.`,
      ],
      businessReasons,
    };
  }

  return {
    title: "Transaction considérée comme atypique",
    summary:
      "Cette transaction est signalée par le consensus de détection car plusieurs signaux statistiques ou métier la rendent différente des transactions normales.",
    factors: [
      `Type détecté : ${readableLabel(row.anomaly_type)}.`,
      `Opérateur concerné : ${operator}.`,
      `Zone observée : ${wilaya}.`,
      `Score d'anomalie calculé : ${score}.`,
    ],
    businessReasons,
  };
}

const selectClass =
  "mt-1 h-10 w-full rounded-lg border border-hairline bg-surface px-3 text-sm font-medium text-ink outline-none transition focus:border-anchor focus:ring-2 focus:ring-anchor/20";

export function AnomaliesView({ results }: AnomaliesViewProps) {
  const [wilaya, setWilaya] = useState("");
  const [operator, setOperator] = useState("");
  const [anomalyType, setAnomalyType] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<AnomalyRow | null>(null);

  const rows = useMemo<AnomalyRow[]>(() => {
    const ensemble = results.find((result) => result.algorithm === "ensemble");
    return (ensemble?.preview ?? []).map((transaction) => ({
      ...transaction,
      model: "ensemble",
    }));
  }, [results]);

  const filteredRows = useMemo(
    () =>
      rows.filter((row) => {
        const rowWilaya = row.sender_wilaya ?? row.receiver_wilaya ?? "";
        return (
          (!wilaya || rowWilaya === wilaya) &&
          (!operator || row.operator === operator) &&
          (!anomalyType || row.anomaly_type === anomalyType)
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
    () =>
      [...new Set(rows.map((row) => row.sender_wilaya ?? row.receiver_wilaya ?? "").filter(Boolean))].sort(),
    [rows],
  );
  const anomalyTypes = useMemo(() => uniqueValues(rows, "anomaly_type"), [rows]);
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
      <section className="dashboard-card p-6 text-sm font-medium text-ink-muted">
        Televersez un fichier pour afficher les transactions suspectes.
      </section>
    );
  }

  return (
    <section className="space-y-4" aria-label="Vue anomalies">
      <motion.div
        className="dashboard-card p-4"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <span
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-anchor-weak text-anchor"
              aria-hidden="true"
            >
              <SlidersHorizontal className="h-4 w-4" />
            </span>
            Filtres
          </div>
          <button
            className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-hairline px-3 text-xs font-semibold text-ink-muted transition-colors hover:bg-canvas hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!hasFilters}
            onClick={resetFilters}
            type="button"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            Réinitialiser
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-muted">
            Wilaya
            <select
              aria-label="Filtrer par wilaya"
              className={selectClass}
              onChange={(event) => setWilaya(event.target.value)}
              value={wilaya}
            >
              <option value="">Toutes</option>
              {wilayas.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>

          <label className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-muted">
            Opérateur
            <select
              aria-label="Filtrer par opérateur"
              className={selectClass}
              onChange={(event) => setOperator(event.target.value)}
              value={operator}
            >
              <option value="">Tous</option>
              {uniqueValues(rows, "operator").map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>

          <label className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-muted">
            Type d'anomalie
            <select
              aria-label="Filtrer par type d'anomalie"
              className={selectClass}
              onChange={(event) => setAnomalyType(event.target.value)}
              value={anomalyType}
            >
              <option value="">Tous</option>
              {anomalyTypes.map((value) => (
                <option key={value} value={value}>
                  {readableLabel(value)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </motion.div>

      <motion.div
        className="dashboard-card overflow-hidden"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.06, duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="soft-scrollbar max-h-[560px] overflow-auto">
          <table className="w-full min-w-[1240px] table-fixed text-left text-[13px]">
            <thead className="sticky top-0 z-10 bg-canvas text-[11px] uppercase tracking-[0.04em] text-ink-muted">
              <tr>
                <th className="w-[9.5rem] px-4 py-2.5 font-semibold">Date</th>
                <th className="w-[17rem] px-4 py-2.5 font-semibold">Transaction</th>
                <th className="w-24 px-4 py-2.5 font-semibold">Score</th>
                <th className="w-40 px-4 py-2.5 font-semibold">Type</th>
                <th className="w-40 px-4 py-2.5 font-semibold">Wilaya</th>
                <th className="w-32 px-4 py-2.5 font-semibold">Opérateur</th>
                <th className="w-36 px-4 py-2.5 font-semibold">Montant</th>
                <th className="w-28 px-4 py-2.5 font-semibold">Statut</th>
                <th className="w-20 px-4 py-2.5 text-center font-semibold">Détails</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {paginatedRows.map((row, index) => {
                const wilayaName = row.sender_wilaya ?? row.receiver_wilaya ?? "-";

                return (
                  <tr
                    className="text-ink transition-colors hover:bg-anchor-weak/60"
                    key={`${row.model}-${row.transaction_id ?? startIndex + index}`}
                  >
                    <td className="tnum whitespace-nowrap px-4 py-3 font-mono text-xs text-ink-muted">
                      {formatDate(row.timestamp)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="block max-w-[15rem] truncate font-mono text-xs text-ink"
                        title={row.transaction_id ?? "-"}
                      >
                        {row.transaction_id ?? "-"}
                      </span>
                    </td>
                    <td className="tnum px-4 py-3 font-mono text-xs font-medium text-ink">
                      {Number(row.anomaly_score ?? 0).toFixed(3)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-md px-2 py-1 text-xs font-semibold ${typeBadge}`}>
                        {readableLabel(row.anomaly_type)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="block max-w-[9rem] whitespace-normal leading-5" title={wilayaName}>
                        {wilayaName}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="block truncate" title={row.operator ?? "-"}>
                        {row.operator ?? "-"}
                      </span>
                    </td>
                    <td className="tnum whitespace-nowrap px-4 py-3 font-medium text-ink">
                      {formatAmount(row.amount)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-md px-2 py-1 text-xs font-semibold ${statusBadge(row.status)}`}
                      >
                        {row.status ?? "-"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        aria-label={`Voir ${row.transaction_id ?? "la transaction"}`}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-hairline text-ink-muted transition-colors hover:border-anchor/40 hover:bg-anchor-weak hover:text-anchor"
                        onClick={() => setSelected(row)}
                        type="button"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {filteredRows.length === 0 ? (
                <tr>
                  <td className="px-4 py-10 text-center text-sm text-ink-muted" colSpan={9}>
                    Aucune transaction ne correspond aux filtres sélectionnés.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </motion.div>

      <div className="dashboard-card flex flex-col gap-3 px-3 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
        <div className="tnum text-xs font-medium text-ink-muted">
          {filteredRows.length > 0
            ? `${(startIndex + 1).toLocaleString("fr-FR")} – ${endIndex.toLocaleString("fr-FR")} sur ${filteredRows.length.toLocaleString("fr-FR")} anomalies`
            : "0 anomalie"}
        </div>
        <div className="flex items-center gap-2">
          <button
            className="inline-flex items-center gap-1.5 rounded-lg border border-hairline px-3 py-1.5 text-xs font-semibold text-ink-muted transition-colors hover:bg-canvas hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
            disabled={currentPage <= 1}
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            type="button"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Precedent
          </button>
          <span className="tnum min-w-24 text-center text-xs font-medium text-ink-muted">
            Page {currentPage.toLocaleString("fr-FR")} / {pageCount.toLocaleString("fr-FR")}
          </span>
          <button
            className="inline-flex items-center gap-1.5 rounded-lg border border-hairline px-3 py-1.5 text-xs font-semibold text-ink-muted transition-colors hover:bg-canvas hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
            disabled={currentPage >= pageCount}
            onClick={() => setPage((value) => Math.min(pageCount, value + 1))}
            type="button"
          >
            Suivant
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {selected
        ? (() => {
            const explanation = explainAnomaly(selected);

            return (
              <div
                className="fixed inset-0 z-[1000] flex items-center justify-center bg-ink/40 p-4"
                role="dialog"
              >
                <div className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-xl border border-hairline bg-surface shadow-pop">
                  <header className="flex items-start justify-between gap-4 border-b border-hairline bg-canvas p-5">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-muted">
                        Détails de détection
                      </p>
                      <h3 className="mt-1 text-lg font-semibold text-ink">{explanation.title}</h3>
                      <p className="mt-1 max-w-2xl font-mono text-xs text-ink-muted">
                        Transaction {selected.transaction_id ?? "-"}
                      </p>
                    </div>
                    <button
                      aria-label="Fermer les details"
                      className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-hairline text-ink-muted transition-colors hover:bg-canvas hover:text-ink"
                      onClick={() => setSelected(null)}
                      type="button"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </header>

                  <div className="space-y-4 p-5">
                    <div className="rounded-xl border border-anchor/20 bg-anchor-weak p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-anchor">
                        Pourquoi cette transaction est suspecte
                      </p>
                      <p className="mt-2 text-sm leading-6 text-ink">{explanation.summary}</p>
                    </div>

                    <div className="grid gap-3 md:grid-cols-4">
                      <div className="rounded-lg border border-hairline p-3">
                        <p className="text-[11px] font-semibold uppercase text-ink-faint">Type</p>
                        <span className={`mt-2 inline-flex rounded-md px-2 py-1 text-xs font-semibold ${typeBadge}`}>
                          {readableLabel(selected.anomaly_type)}
                        </span>
                      </div>
                      <div className="rounded-lg border border-hairline p-3">
                        <p className="text-[11px] font-semibold uppercase text-ink-faint">Score</p>
                        <p className="tnum mt-2 font-mono text-sm font-semibold text-ink">
                          {Number(selected.anomaly_score ?? 0).toFixed(3)}
                        </p>
                      </div>
                      <div className="rounded-lg border border-hairline p-3">
                        <p className="text-[11px] font-semibold uppercase text-ink-faint">Montant</p>
                        <p className="tnum mt-2 text-sm font-semibold text-ink">{formatAmount(selected.amount)}</p>
                      </div>
                      <div className="rounded-lg border border-hairline p-3">
                        <p className="text-[11px] font-semibold uppercase text-ink-faint">Statut</p>
                        <span
                          className={`mt-2 inline-flex rounded-md px-2 py-1 text-xs font-semibold ${statusBadge(selected.status)}`}
                        >
                          {selected.status ?? "-"}
                        </span>
                      </div>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                      <section className="rounded-xl border border-hairline p-4">
                        <h4 className="text-sm font-semibold text-ink">
                          Facteurs qui expliquent la détection
                        </h4>
                        <ul className="mt-3 space-y-2">
                          {explanation.factors.map((factor) => (
                            <li
                              className="flex gap-2 text-sm leading-6 text-ink-muted"
                              key={factor}
                            >
                              <span
                                aria-hidden="true"
                                className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-anchor"
                              />
                              <span>{factor}</span>
                            </li>
                          ))}
                        </ul>
                      </section>

                      <section className="rounded-xl border border-hairline bg-canvas p-4">
                        <h4 className="text-sm font-semibold text-ink">Contexte transaction</h4>
                        <dl className="mt-3 space-y-3 text-sm">
                          <div>
                            <dt className="text-[11px] font-semibold uppercase text-ink-faint">Date</dt>
                            <dd className="tnum mt-1 font-medium text-ink">{formatDate(selected.timestamp)}</dd>
                          </div>
                          <div>
                            <dt className="text-[11px] font-semibold uppercase text-ink-faint">Wilaya</dt>
                            <dd className="mt-1 font-medium text-ink">
                              {selected.sender_wilaya ?? selected.receiver_wilaya ?? "-"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-[11px] font-semibold uppercase text-ink-faint">Opérateur</dt>
                            <dd className="mt-1 font-medium text-ink">{selected.operator ?? "-"}</dd>
                          </div>
                        </dl>
                      </section>
                    </div>

                    {explanation.businessReasons.length > 0 ? (
                      <section className="rounded-xl border border-alert/20 bg-alert-weak p-4">
                        <h4 className="text-sm font-semibold text-alert">Règles métier déclenchées</h4>
                        <ul className="mt-3 space-y-2">
                          {explanation.businessReasons.map((reason) => (
                            <li className="flex gap-2 text-sm leading-6 text-alert" key={reason}>
                              <span
                                aria-hidden="true"
                                className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-alert"
                              />
                              <span>{reason}</span>
                            </li>
                          ))}
                        </ul>
                      </section>
                    ) : null}

                    <details className="rounded-xl border border-hairline p-4">
                      <summary className="cursor-pointer text-sm font-semibold text-ink">
                        Données techniques complètes
                      </summary>
                      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                        {Object.entries(selected).map(([key, value]) => (
                          <div className="rounded-lg bg-canvas p-3" key={key}>
                            <dt className="text-[11px] uppercase text-ink-muted">{key}</dt>
                            <dd className="mt-1 break-words font-mono text-xs text-ink">{String(value ?? "-")}</dd>
                          </div>
                        ))}
                      </dl>
                    </details>
                  </div>
                </div>
              </div>
            );
          })()
        : null}
    </section>
  );
}
