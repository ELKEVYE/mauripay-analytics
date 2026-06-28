import { useMemo, useState } from "react";
import { AlertTriangle, Banknote, CheckCircle2, ReceiptText } from "lucide-react";
import { motion } from "framer-motion";
import {
  apiClient,
  type ApiSnapshot,
  type ModelPredictionResult,
} from "./api/client";
import { StatCard } from "./components/StatCard";
import { AnomalyAnalysisView, TransactionsAnalysisView } from "./views/AnalysisPages";
import { AppLayout, type AppView } from "./views/AppLayout";
import { Dashboard } from "./views/Dashboard";

function formatNumber(value: number) {
  return new Intl.NumberFormat("fr-FR").format(Math.round(value));
}

function formatAmount(value: number) {
  return `${formatNumber(value)} MRU`;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)} %`;
}

function datasetFileName(path: string) {
  return path.split(/[\\/]/).pop() ?? path;
}

export default function App() {
  const [activeView, setActiveView] = useState<AppView>("dashboard");
  const [datasetPath, setDatasetPath] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [snapshot, setSnapshot] = useState<ApiSnapshot | null>(null);
  const [predictionResults, setPredictionResults] = useState<ModelPredictionResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiReachable, setApiReachable] = useState<boolean | null>(null);

  const ensembleResult = useMemo(
    () => predictionResults.find((result) => result.algorithm === "ensemble"),
    [predictionResults],
  );

  async function uploadAndPredict() {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    try {
      const ingestion = await apiClient.uploadDataset(selectedFile);
      if (ingestion.invalid_rows > 0) {
        throw new Error(
          `${ingestion.invalid_rows} ligne(s) invalide(s). Rapport : ${ingestion.errors_file ?? "indisponible"}`,
        );
      }

      const prediction = await apiClient.predictAll(ingestion.dataset_path);
      setPredictionResults(prediction.results);

      const dashboardResult =
        prediction.results.find((result) => result.algorithm === "ensemble")
        ?? prediction.results[0];
      if (!dashboardResult) {
        throw new Error("Aucun résultat de prédiction reçu.");
      }

      setDatasetPath(dashboardResult.output_path);
      setSnapshot(await apiClient.getSnapshot(dashboardResult.output_path));
      setApiReachable(true);
    } catch (apiError) {
      setApiReachable(false);
      setError(apiError instanceof Error ? apiError.message : "Erreur API inconnue");
    } finally {
      setLoading(false);
    }
  }

  async function refreshSnapshot() {
    if (!datasetPath) return;

    setLoading(true);
    setError(null);
    try {
      setSnapshot(await apiClient.getSnapshot(datasetPath));
      setApiReachable(true);
    } catch (apiError) {
      setApiReachable(false);
      setError(apiError instanceof Error ? apiError.message : "Erreur API inconnue");
    } finally {
      setLoading(false);
    }
  }

  async function reconnectApi() {
    setLoading(true);
    setError(null);
    try {
      await apiClient.getHealth("stats");
      setApiReachable(true);
      if (datasetPath) {
        setSnapshot(await apiClient.getSnapshot(datasetPath));
      }
    } catch (apiError) {
      setApiReachable(false);
      setError(apiError instanceof Error ? apiError.message : "API indisponible");
    } finally {
      setLoading(false);
    }
  }

  function renderActivePage() {
    switch (activeView) {
      case "dashboard":
        return (
          <Dashboard
            datasetPath={datasetPath}
            loading={loading}
            selectedFile={selectedFile}
            onFileChange={setSelectedFile}
            onSubmit={uploadAndPredict}
          />
        );
      case "transactionTemporal":
        return <TransactionsAnalysisView activeSubPage="temporal" snapshot={snapshot} />;
      case "transactionOperations":
        return <TransactionsAnalysisView activeSubPage="operations" snapshot={snapshot} />;
      case "transactionGeography":
        return <TransactionsAnalysisView activeSubPage="geography" snapshot={snapshot} />;
      case "anomalyTemporal":
        return <AnomalyAnalysisView activeSubPage="temporal" results={predictionResults} snapshot={snapshot} />;
      case "anomalyGeography":
        return <AnomalyAnalysisView activeSubPage="geography" results={predictionResults} snapshot={snapshot} />;
      case "anomalyTransactions":
        return <AnomalyAnalysisView activeSubPage="transactions" results={predictionResults} snapshot={snapshot} />;
    }
  }

  return (
    <AppLayout
      activeView={activeView}
      anomalyCount={ensembleResult?.anomalies_detected ?? 0}
      apiConnected={!error && (apiReachable ?? Boolean(snapshot))}
      datasetName={datasetPath ? datasetFileName(datasetPath) : ""}
      onNavigate={setActiveView}
      onReconnect={reconnectApi}
      onRefresh={refreshSnapshot}
      refreshing={loading}
    >
      <main className="mx-auto flex w-full min-w-0 max-w-7xl flex-col gap-6 px-5 py-6 md:px-6">
        {error ? (
          <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-mauri-red">
            {error}
          </div>
        ) : null}

        {activeView === "dashboard" ? renderActivePage() : null}

        {activeView === "dashboard" ? (
        <motion.div
          className="grid w-full gap-4 md:grid-cols-2 xl:grid-cols-4 xl:gap-3"
          aria-label="Indicateurs principaux"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: {
              transition: {
                delayChildren: 0.16,
                staggerChildren: 0.12,
              },
            },
          }}
        >
          <StatCard
            detail="Volume total du dataset chargé"
            icon={ReceiptText}
            status="Dataset charge"
            title="Transactions"
            value={formatNumber(snapshot?.stats.total_transactions ?? 0)}
          />
          <StatCard
            detail="Somme des montants observés"
            icon={Banknote}
            nowrapValue
            status="Analyse terminee"
            title="Montant total"
            tone="gold"
            value={formatAmount(snapshot?.stats.total_amount ?? 0)}
          />
          <StatCard
            detail={
              ensembleResult
                ? `${formatNumber(ensembleResult.total_transactions)} transactions analysées`
                : "Chargez un fichier pour lancer l'analyse"
            }
            icon={AlertTriangle}
            status="Consensus actif"
            title="Consensus des trois modèles"
            tone="red"
            value={
              ensembleResult
                ? `${formatNumber(ensembleResult.anomalies_detected)} fraudes détectées`
                : "—"
            }
          />
          <StatCard
            detail="Part des transactions échouées"
            icon={CheckCircle2}
            status="Echecs detectes"
            title="Taux d'échec"
            tone="blue"
            value={formatPercent(snapshot?.stats.failure_rate ?? 0)}
          />
        </motion.div>
        ) : null}

        {activeView !== "dashboard" ? renderActivePage() : null}
      </main>
    </AppLayout>
  );
}
