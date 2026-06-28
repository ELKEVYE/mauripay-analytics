import { BrainCircuit, CheckCircle2, GitMerge, ShieldAlert } from "lucide-react";
import { useMemo } from "react";
import type { ApiSnapshot, GeoWilaya, ModelStatus } from "../api/client";
import { DataTable } from "../components/DataTable";

type DetectionModelsViewProps = {
  snapshot: ApiSnapshot | null;
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("fr-FR").format(Math.round(value));
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)} %`;
}

function topAnomalyWilayas(wilayas: GeoWilaya[]) {
  return [...wilayas].sort((a, b) => b.anomalies_count - a.anomalies_count).slice(0, 8);
}

function AnomalyBadge({ value }: { value: number }) {
  const tone =
    value >= 150
      ? "bg-rose-50 text-rose-700 ring-rose-100"
      : value >= 50
        ? "bg-orange-50 text-orange-700 ring-orange-100"
        : "bg-emerald-50 text-emerald-700 ring-emerald-100";

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-extrabold ring-1 ${tone}`}>
      {formatNumber(value)}
    </span>
  );
}

function FailureBadge({ value }: { value: number }) {
  const percent = value * 100;
  const tone =
    percent >= 0.6
      ? "bg-rose-50 text-rose-700 ring-rose-100"
      : percent >= 0.4
        ? "bg-orange-50 text-orange-700 ring-orange-100"
        : "bg-emerald-50 text-emerald-700 ring-emerald-100";

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-extrabold ring-1 ${tone}`}>
      {formatPercent(value)}
    </span>
  );
}

const MODEL_DETAILS: Record<string, { name: string; role: string; tone: string }> = {
  autoencoder: {
    name: "Autoencoder",
    role: "Repere les transactions eloignees des comportements habituels.",
    tone: "from-rose-50 to-white border-rose-100 text-rose-700",
  },
  isolation_forest: {
    name: "Isolation Forest",
    role: "Isole les transactions rares et atypiques dans le dataset.",
    tone: "from-emerald-50 to-white border-emerald-100 text-mauri-green",
  },
  lof: {
    name: "Local Outlier Factor",
    role: "Compare chaque transaction avec son voisinage local.",
    tone: "from-blue-50 to-white border-blue-100 text-blue-700",
  },
  ensemble: {
    name: "Consensus",
    role: "Combine les signaux des trois modeles pour produire la decision finale.",
    tone: "from-violet-50 to-white border-violet-100 text-violet-700",
  },
};

function modelName(algorithm: string) {
  return MODEL_DETAILS[algorithm]?.name ?? algorithm;
}

function modelRole(algorithm: string) {
  return MODEL_DETAILS[algorithm]?.role ?? "Modele de detection des anomalies.";
}

function modelTone(algorithm: string) {
  return MODEL_DETAILS[algorithm]?.tone ?? "from-slate-50 to-white border-slate-100 text-slate-700";
}

function ModelCard({ model }: { model: ModelStatus }) {
  const operational = model.trained;

  return (
    <article className={`dashboard-card bg-gradient-to-br ${modelTone(model.algorithm)} p-4`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-extrabold text-ink">{modelName(model.algorithm)}</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">{modelRole(model.algorithm)}</p>
        </div>
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-white/80 shadow-sm">
          <BrainCircuit className="h-5 w-5" aria-hidden="true" />
        </span>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${
            operational ? "bg-emerald-50 text-mauri-green" : "bg-slate-100 text-slate-500"
          }`}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          {operational ? "Operationnel" : "Indisponible"}
        </span>
        <span className="rounded-full bg-white/80 px-2.5 py-1 text-xs font-semibold text-slate-500">
          Actif
        </span>
      </div>
    </article>
  );
}

export function DetectionModelsView({ snapshot }: DetectionModelsViewProps) {
  const anomalyWilayas = useMemo(
    () => topAnomalyWilayas(snapshot?.geo.wilayas ?? []),
    [snapshot?.geo.wilayas],
  );
  const models = snapshot?.models.models ?? [];

  return (
    <section
      className="grid gap-4 lg:h-[calc(100vh-15rem)] lg:min-h-[440px] lg:grid-rows-[1fr_auto]"
      aria-label="Detection et modeles"
    >
      <DataTable
        compact
        columns={[
          { key: "wilaya", label: "Wilaya" },
          {
            key: "anomalies_count",
            label: "Anomalies",
            render: (row) => <AnomalyBadge value={Number(row.anomalies_count)} />,
          },
          {
            key: "transactions",
            label: "Transactions",
            render: (row) => formatNumber(Number(row.transactions)),
          },
          {
            key: "failure_rate",
            label: "Taux d'echec",
            render: (row) => <FailureBadge value={Number(row.failure_rate)} />,
          },
        ]}
        rows={anomalyWilayas}
        title="Classement geographique des anomalies"
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr_1fr_1.25fr]">
        {models.filter((model) => model.algorithm !== "ensemble").map((model) => (
          <ModelCard key={model.algorithm} model={model} />
        ))}
        <section className="dashboard-card p-4">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-rose-50 text-rose-700 shadow-sm">
              <GitMerge className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-sm font-extrabold text-ink">Consensus des trois modeles</h2>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                La decision finale combine Isolation Forest, LOF et Autoencoder pour garder les alertes les plus utiles.
              </p>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 rounded bg-rose-50 px-3 py-2 text-xs font-semibold text-rose-700">
            <ShieldAlert className="h-4 w-4" />
            Les anomalies affichees dans l'interface viennent du resultat ensemble.
          </div>
        </section>
      </div>
    </section>
  );
}
