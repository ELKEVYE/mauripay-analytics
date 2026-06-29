import { useMemo } from "react";
import { motion } from "framer-motion";
import type { Variants } from "framer-motion";
import {
  AlertTriangle,
  Banknote,
  BarChart3,
  Cable,
  CalendarDays,
  Clock3,
  Donut,
  MapPinned,
  TrendingUp,
} from "lucide-react";
import Plot from "react-plotly.js";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ApiSnapshot, GeoWilaya, ModelPredictionResult } from "../api/client";
import { DataTable } from "../components/DataTable";
import { GeoMap } from "../components/GeoMap";
import { HourlyHeatmap } from "../components/HourlyHeatmap";
import { AnomaliesView } from "./AnomaliesView";

type SnapshotProps = {
  snapshot: ApiSnapshot | null;
};

type TransactionAnalysisViewProps = SnapshotProps & {
  activeSubPage: "temporal" | "operations" | "geography";
};

type AnomalyAnalysisViewProps = SnapshotProps & {
  activeSubPage: "temporal" | "geography" | "transactions";
  results: ModelPredictionResult[];
};

const axisStyle = {
  axisLine: false,
  tickLine: false,
  tick: { fill: "#64748b", fontSize: 11 },
};

const headerToneClasses = {
  blue: "bg-blue-50 text-blue-600",
  green: "bg-emerald-50 text-mauri-green",
  orange: "bg-orange-50 text-orange-600",
  red: "bg-rose-50 text-rose-600",
  violet: "bg-violet-50 text-violet-600",
};

const anomalyGridVariants: Variants = {
  hidden: {},
  visible: {
    transition: {
      delayChildren: 0.08,
      staggerChildren: 0.11,
    },
  },
};

const anomalyCardVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.985 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.48, ease: [0.22, 1, 0.36, 1] },
  },
};

const anomalyCardHover = {
  y: -4,
  boxShadow: "0 18px 34px -24px rgba(15, 23, 42, 0.38)",
  transition: { duration: 0.22, ease: "easeOut" as const },
};

function formatNumber(value: number) {
  return new Intl.NumberFormat("fr-FR").format(Math.round(value));
}

function formatAmount(value: number) {
  return `${formatNumber(value)} MRU`;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)} %`;
}

function entriesToChart(data: Record<string, number>) {
  return Object.entries(data).map(([name, value]) => ({ name, value }));
}

function countByField<T extends Record<string, unknown>>(rows: T[], field: keyof T) {
  return rows.reduce<Record<string, number>>((accumulator, row) => {
    const rawValue = row[field];
    const key = typeof rawValue === "string" && rawValue.trim() ? rawValue.trim() : "Non renseigne";
    accumulator[key] = (accumulator[key] ?? 0) + 1;
    return accumulator;
  }, {});
}

function topTransactionsWilayas(wilayas: GeoWilaya[]) {
  return [...wilayas].sort((a, b) => b.transactions - a.transactions).slice(0, 8);
}

function topAnomalyWilayas(wilayas: GeoWilaya[]) {
  return [...wilayas].sort((a, b) => b.anomalies_count - a.anomalies_count).slice(0, 8);
}

function ChartHeader({
  title,
  description,
  icon: Icon,
  tone,
}: {
  title: string;
  description: string;
  icon: typeof TrendingUp;
  tone: keyof typeof headerToneClasses;
}) {
  return (
    <header className="mb-3 flex items-start gap-3">
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded ${headerToneClasses[tone]}`}>
        <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
      </span>
      <div>
        <h2 className="text-sm font-extrabold text-ink">{title}</h2>
        <p className="mt-0.5 text-xs font-medium text-slate-500">{description}</p>
      </div>
    </header>
  );
}

function AnomalyBadge({ value }: { value: number }) {
  const tone =
    value >= 150
      ? "bg-rose-50 text-rose-700 ring-rose-100"
      : value >= 50
        ? "bg-orange-50 text-orange-700 ring-orange-100"
        : "bg-emerald-50 text-emerald-700 ring-emerald-100";

  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-extrabold ring-1 ${tone}`}>
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
    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-extrabold ring-1 ${tone}`}>
      {formatPercent(value)}
    </span>
  );
}

export function TransactionsAnalysisView({ activeSubPage, snapshot }: TransactionAnalysisViewProps) {
  const typeChart = useMemo(
    () => entriesToChart(snapshot?.stats.by_type ?? {}),
    [snapshot?.stats.by_type],
  );
  const channelChart = useMemo(
    () => entriesToChart(snapshot?.stats.by_channel ?? {}),
    [snapshot?.stats.by_channel],
  );
  const operatorRows = useMemo(
    () => [...(snapshot?.timeseries.volume_by_operator ?? [])].sort((a, b) => b.transactions - a.transactions),
    [snapshot?.timeseries.volume_by_operator],
  );
  const wilayas = useMemo(
    () => topTransactionsWilayas(snapshot?.geo.wilayas ?? []),
    [snapshot?.geo.wilayas],
  );
  return (
    <section className="flex flex-col gap-4" aria-label="Analyse des transactions">
      {activeSubPage === "temporal" ? (
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="dashboard-card chart-card min-h-[310px] border-emerald-100 bg-gradient-to-br from-white via-white to-emerald-50/35">
          <ChartHeader
            description="Evolution quotidienne du volume traite"
            icon={TrendingUp}
            title="Transactions par jour"
            tone="green"
          />
          <div className="min-h-[205px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={snapshot?.timeseries.transactions_by_day ?? []} margin={{ top: 8, right: 14, left: -8, bottom: 0 }}>
                <defs>
                  <linearGradient id="transactionsOnlyGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={0.32} />
                    <stop offset="95%" stopColor="#059669" stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="day" minTickGap={30} {...axisStyle} />
                <YAxis {...axisStyle} />
                <Tooltip />
                <Area
                  activeDot={{ r: 5, stroke: "#ffffff", strokeWidth: 2 }}
                  dataKey="transactions"
                  dot={{ r: 2, strokeWidth: 1 }}
                  fill="url(#transactionsOnlyGradient)"
                  stroke="#059669"
                  strokeWidth={2.5}
                  type="monotone"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="dashboard-card chart-card min-h-[310px] border-orange-100 bg-gradient-to-br from-white via-white to-orange-50/35">
          <ChartHeader
            description="Montants observes par jour"
            icon={Banknote}
            title="Montants par jour"
            tone="orange"
          />
          <div className="min-h-[205px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={snapshot?.timeseries.amounts_by_day ?? []} margin={{ top: 8, right: 14, left: 5, bottom: 0 }}>
                <defs>
                  <linearGradient id="amountsOnlyGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.36} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="day" minTickGap={30} {...axisStyle} />
                <YAxis width={70} {...axisStyle} />
                <Tooltip />
                <Area
                  activeDot={{ r: 5, stroke: "#ffffff", strokeWidth: 2 }}
                  dataKey="total_amount"
                  dot={{ r: 2, strokeWidth: 1 }}
                  fill="url(#amountsOnlyGradient)"
                  stroke="#f59e0b"
                  strokeWidth={2.5}
                  type="monotone"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      ) : null}

      {activeSubPage === "operations" ? (
      <div className="grid gap-4 lg:grid-cols-2">
        <HourlyHeatmap compact rows={snapshot?.timeseries.hourly_heatmap ?? []} />

        <div className="dashboard-card chart-card min-h-[360px] border-blue-100 bg-gradient-to-br from-white via-white to-blue-50/45">
          <ChartHeader
            description="Transactions traitees par operateur"
            icon={BarChart3}
            title="Volume par operateur"
            tone="blue"
          />
          <div className="min-h-[255px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                barCategoryGap={10}
                data={operatorRows}
                layout="vertical"
                margin={{ top: 4, right: 58, left: 8, bottom: 0 }}
              >
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" horizontal={false} />
                <XAxis type="number" {...axisStyle} />
                <YAxis dataKey="operator" type="category" width={120} {...axisStyle} />
                <Tooltip />
                <Bar dataKey="transactions" fill="#0f766e" radius={[0, 8, 8, 0]} barSize={14}>
                  <LabelList
                    className="fill-slate-600 text-[11px] font-bold"
                    dataKey="transactions"
                    formatter={(value: number) => formatNumber(value)}
                    position="right"
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="dashboard-card chart-card min-h-[360px] border-violet-100 bg-gradient-to-br from-white via-white to-violet-50/45">
          <ChartHeader
            description="Part des transactions par categorie"
            icon={Donut}
            title="Repartition par type"
            tone="violet"
          />
          <div className="flex min-h-[255px] flex-1 items-center justify-center">
            <Plot
              config={{ displayModeBar: false, responsive: true }}
              data={[
                {
                  labels: typeChart.map((item) => item.name),
                  values: typeChart.map((item) => item.value),
                  type: "pie",
                  hole: 0.58,
                  textinfo: "percent",
                  textposition: "outside",
                  hovertemplate: "%{label}<br>%{value:,} transactions<br>%{percent}<extra></extra>",
                  marker: {
                    colors: ["#047857", "#f59e0b", "#e11d48", "#2563eb", "#64748b", "#7c3aed"],
                    line: { color: "#ffffff", width: 3 },
                  },
                },
              ]}
              layout={{
                autosize: true,
                margin: { l: 8, r: 8, t: 8, b: 8 },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
                showlegend: true,
                legend: {
                  orientation: "v",
                  x: 1,
                  y: 0.5,
                  xanchor: "left",
                  font: { size: 11, color: "#334155" },
                },
              }}
              useResizeHandler
              style={{ width: "100%", height: "100%" }}
            />
          </div>
        </div>

        <div className="dashboard-card chart-card min-h-[360px] border-teal-100 bg-gradient-to-br from-white via-white to-teal-50/45">
          <ChartHeader
            description="Volume par canal de transaction"
            icon={Cable}
            title="Canaux utilises"
            tone="green"
          />
          <div className="min-h-[255px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart barCategoryGap={28} data={channelChart} margin={{ top: 8, right: 24, left: -4, bottom: 0 }}>
                <defs>
                  <linearGradient id="transactionChannelsGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#059669" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#0f766e" stopOpacity={0.8} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="name" {...axisStyle} />
                <YAxis {...axisStyle} />
                <Tooltip />
                <Bar dataKey="value" fill="url(#transactionChannelsGradient)" radius={[8, 8, 2, 2]} maxBarSize={82}>
                  <LabelList
                    className="fill-slate-600 text-[11px] font-bold"
                    dataKey="value"
                    formatter={(value: number) => formatNumber(value)}
                    position="top"
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      ) : null}

      {activeSubPage === "geography" ? (
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="dashboard-card chart-card min-h-[345px] border-emerald-100 bg-gradient-to-br from-white via-white to-emerald-50/40">
          <ChartHeader
            description="Wilayas avec le plus grand volume"
            icon={MapPinned}
            title="Transactions par wilaya"
            tone="green"
          />
          <div className="min-h-[240px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={wilayas} layout="vertical" margin={{ top: 4, right: 62, left: 8, bottom: 0 }}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" horizontal={false} />
                <XAxis type="number" {...axisStyle} />
                <YAxis dataKey="wilaya" type="category" width={132} {...axisStyle} />
                <Tooltip formatter={(value) => formatNumber(Number(value))} />
                <Bar dataKey="transactions" fill="#047857" radius={[0, 8, 8, 0]} barSize={14}>
                  <LabelList
                    className="fill-slate-600 text-[11px] font-bold"
                    dataKey="transactions"
                    formatter={(value: number) => formatNumber(value)}
                    position="right"
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <GeoMap compact wilayas={snapshot?.geo.wilayas ?? []} />

        <div className="lg:col-span-2">
          <DataTable
            columns={[
              { key: "wilaya", label: "Wilaya" },
              {
                key: "transactions",
                label: "Transactions",
                render: (row) => formatNumber(Number(row.transactions)),
              },
              {
                key: "total_amount",
                label: "Montant",
                render: (row) => formatAmount(Number(row.total_amount)),
              },
              {
                key: "failure_rate",
                label: "Taux d'echec",
                render: (row) => <FailureBadge value={Number(row.failure_rate)} />,
              },
            ]}
            rows={wilayas}
            tone="green"
            title="Wilayas principales"
          />
        </div>
      </div>
      ) : null}
    </section>
  );
}

export function AnomalyAnalysisView({ activeSubPage, snapshot, results }: AnomalyAnalysisViewProps) {
  const anomalyWilayas = useMemo(
    () => topAnomalyWilayas(snapshot?.geo.wilayas ?? []),
    [snapshot?.geo.wilayas],
  );
  const ensembleAnomalies = useMemo(
    () => results.find((result) => result.algorithm === "ensemble")?.preview ?? [],
    [results],
  );
  const typeChart = useMemo(
    () => entriesToChart(countByField(ensembleAnomalies, "transaction_type")),
    [ensembleAnomalies],
  );
  const channelChart = useMemo(
    () => entriesToChart(countByField(ensembleAnomalies, "channel")),
    [ensembleAnomalies],
  );
  const anomalyTypeTotal = typeChart.reduce((total, item) => total + item.value, 0);
  const anomalyChannelMax = Math.max(...channelChart.map((item) => item.value), 1);

  return (
    <section className="flex flex-col gap-4" aria-label="Analyse des anomalies">
      {activeSubPage === "temporal" ? (
      <motion.div
        animate="visible"
        className="grid gap-4 lg:grid-cols-2"
        initial="hidden"
        variants={anomalyGridVariants}
      >
        <motion.div
          className="dashboard-card chart-card min-h-[310px] border-rose-100 bg-gradient-to-br from-white via-white to-rose-50/45"
          variants={anomalyCardVariants}
          whileHover={anomalyCardHover}
        >
          <ChartHeader
            description="Repartition horaire des transactions suspectes"
            icon={AlertTriangle}
            title="Anomalies par heure"
            tone="red"
          />
          <div className="min-h-[205px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={snapshot?.timeseries.anomalies_by_hour ?? []} margin={{ top: 8, right: 14, left: -8, bottom: 0 }}>
                <defs>
                  <linearGradient id="anomalyHoursGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#e11d48" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#fb7185" stopOpacity={0.65} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="hour" {...axisStyle} />
                <YAxis {...axisStyle} />
                <Tooltip />
                <Bar
                  animationBegin={180}
                  animationDuration={850}
                  animationEasing="ease-out"
                  dataKey="anomalies"
                  fill="url(#anomalyHoursGradient)"
                  isAnimationActive
                  radius={[6, 6, 2, 2]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          className="dashboard-card chart-card min-h-[310px] border-violet-100 bg-gradient-to-br from-white via-white to-violet-50/40"
          variants={anomalyCardVariants}
          whileHover={anomalyCardHover}
        >
          <ChartHeader
            description="Evolution hebdomadaire des anomalies"
            icon={CalendarDays}
            title="Anomalies par semaine"
            tone="violet"
          />
          <div className="min-h-[205px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={snapshot?.timeseries.anomalies_by_week ?? []} margin={{ top: 8, right: 14, left: -8, bottom: 0 }}>
                <defs>
                  <linearGradient id="anomalyWeeksGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#dc2626" stopOpacity={0.32} />
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="week" minTickGap={30} {...axisStyle} />
                <YAxis {...axisStyle} />
                <Tooltip />
                <Area
                  activeDot={{ r: 5, stroke: "#ffffff", strokeWidth: 2 }}
                  animationBegin={220}
                  animationDuration={1000}
                  animationEasing="ease-out"
                  dataKey="anomalies"
                  dot={{ r: 2, strokeWidth: 1 }}
                  fill="url(#anomalyWeeksGradient)"
                  stroke="#dc2626"
                  strokeWidth={2.5}
                  type="monotone"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          className="dashboard-card min-h-[360px] border-rose-100 bg-gradient-to-br from-white via-white to-rose-50/35"
          variants={anomalyCardVariants}
          whileHover={anomalyCardHover}
        >
          <ChartHeader
            description="Types presents parmi les anomalies detectees"
            icon={Donut}
            title="Profil des alertes"
            tone="red"
          />
          <div className="grid flex-1 gap-3">
            <div className="rounded-2xl border border-rose-100 bg-white/80 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]">
              <p className="text-[11px] font-black uppercase tracking-[0.08em] text-rose-500">Total alertes classees</p>
              <div className="mt-2 flex items-end justify-between gap-3">
                <p className="text-3xl font-black text-rose-700">{formatNumber(anomalyTypeTotal)}</p>
                <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-extrabold text-rose-700">
                  Ensemble
                </span>
              </div>
            </div>
            <div className="space-y-2.5">
              {typeChart.map((item, index) => {
                const percent = anomalyTypeTotal > 0 ? (item.value / anomalyTypeTotal) * 100 : 0;
                const tone =
                  index === 0
                    ? "from-rose-600 to-orange-500"
                    : index === 1
                      ? "from-orange-500 to-amber-400"
                      : "from-slate-500 to-slate-400";

                return (
                  <motion.div
                    animate={{ opacity: 1, x: 0 }}
                    className="rounded-2xl border border-slate-100 bg-white/85 p-3 shadow-sm"
                    initial={{ opacity: 0, x: -12 }}
                    key={item.name}
                    transition={{ delay: 0.36 + index * 0.07, duration: 0.32 }}
                    whileHover={{ x: 3, backgroundColor: "rgba(255,255,255,1)" }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-extrabold text-ink">{item.name}</p>
                        <p className="text-xs font-semibold text-slate-500">{percent.toFixed(1)} % des alertes</p>
                      </div>
                      <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-black text-rose-700 ring-1 ring-rose-100">
                        {formatNumber(item.value)}
                      </span>
                    </div>
                    <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-100">
                      <motion.div
                        animate={{ width: `${Math.max(percent, item.value > 0 ? 6 : 0)}%` }}
                        className={`h-full rounded-full bg-gradient-to-r ${tone}`}
                        initial={{ width: 0 }}
                        transition={{ delay: 0.5 + index * 0.08, duration: 0.7, ease: "easeOut" }}
                      />
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </motion.div>

        <motion.div
          className="dashboard-card min-h-[360px] border-orange-100 bg-gradient-to-br from-white via-white to-orange-50/35"
          variants={anomalyCardVariants}
          whileHover={anomalyCardHover}
        >
          <ChartHeader
            description="Canaux presents parmi les anomalies detectees"
            icon={Cable}
            title="Canaux exposes"
            tone="orange"
          />
          <div className="grid flex-1 gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            {channelChart.map((item, index) => {
              const percent = anomalyChannelMax > 0 ? (item.value / anomalyChannelMax) * 100 : 0;
              const severity =
                percent >= 80
                  ? { label: "Exposition forte", className: "bg-rose-50 text-rose-700 ring-rose-100" }
                  : percent >= 40
                    ? { label: "Exposition moyenne", className: "bg-orange-50 text-orange-700 ring-orange-100" }
                    : { label: "Exposition faible", className: "bg-emerald-50 text-emerald-700 ring-emerald-100" };

              return (
                <motion.article
                  animate={{ opacity: 1, y: 0 }}
                  className="relative overflow-hidden rounded-2xl border border-orange-100 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                  initial={{ opacity: 0, y: 14 }}
                  key={item.name}
                  transition={{ delay: 0.38 + index * 0.09, duration: 0.35 }}
                  whileHover={{ y: -3, boxShadow: "0 16px 28px -22px rgba(234, 88, 12, 0.55)" }}
                >
                  <span className="absolute -right-6 -top-6 h-20 w-20 rounded-full bg-orange-100/70" />
                  <div className="relative flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-black uppercase tracking-[0.08em] text-slate-400">
                        Canal {index + 1}
                      </p>
                      <h3 className="mt-2 text-lg font-black text-ink">{item.name}</h3>
                    </div>
                    <span className="rounded-2xl bg-gradient-to-br from-rose-500 to-orange-500 px-3 py-2 text-lg font-black text-white shadow-[0_14px_30px_-20px_rgba(244,63,94,0.85)]">
                      {formatNumber(item.value)}
                    </span>
                  </div>
                  <div className="relative mt-5">
                    <div className="mb-2 flex items-center justify-between text-xs font-bold text-slate-500">
                      <span>Niveau relatif</span>
                      <span>{Math.round(percent)} %</span>
                    </div>
                    <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                      <motion.div
                        animate={{ width: `${Math.max(percent, item.value > 0 ? 8 : 0)}%` }}
                        className="h-full rounded-full bg-gradient-to-r from-orange-400 to-rose-500"
                        initial={{ width: 0 }}
                        transition={{ delay: 0.55 + index * 0.09, duration: 0.72, ease: "easeOut" }}
                      />
                    </div>
                  </div>
                  <span className={`relative mt-4 inline-flex rounded-full px-2.5 py-1 text-[11px] font-extrabold ring-1 ${severity.className}`}>
                    {severity.label}
                  </span>
                </motion.article>
              );
            })}
          </div>
        </motion.div>
      </motion.div>
      ) : null}

      {activeSubPage === "geography" ? (
      <motion.div
        animate="visible"
        className="grid gap-4 lg:grid-cols-2"
        initial="hidden"
        variants={anomalyGridVariants}
      >
        <motion.div
          className="dashboard-card chart-card min-h-[345px] border-rose-100 bg-gradient-to-br from-white via-white to-rose-50/45"
          variants={anomalyCardVariants}
          whileHover={anomalyCardHover}
        >
          <ChartHeader
            description="Zones avec le plus de signalements"
            icon={AlertTriangle}
            title="Top wilayas par anomalies"
            tone="red"
          />
          <div className="min-h-[240px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={anomalyWilayas} layout="vertical" margin={{ top: 4, right: 50, left: 8, bottom: 0 }}>
                <defs>
                  <linearGradient id="anomalyWilayasGradient" x1="0" x2="1" y1="0" y2="0">
                    <stop offset="0%" stopColor="#be123c" stopOpacity={0.88} />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity={0.95} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" horizontal={false} />
                <XAxis type="number" {...axisStyle} />
                <YAxis dataKey="wilaya" type="category" width={132} {...axisStyle} />
                <Tooltip formatter={(value) => formatNumber(Number(value))} />
                <Bar
                  animationBegin={160}
                  animationDuration={950}
                  animationEasing="ease-out"
                  barSize={14}
                  dataKey="anomalies_count"
                  fill="url(#anomalyWilayasGradient)"
                  isAnimationActive
                  radius={[0, 8, 8, 0]}
                >
                  <LabelList
                    className="fill-rose-700 text-[11px] font-bold"
                    dataKey="anomalies_count"
                    formatter={(value: number) => formatNumber(value)}
                    position="right"
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div className="min-h-0" variants={anomalyCardVariants} whileHover={anomalyCardHover}>
          <DataTable
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
            tone="violet"
            title="Classement geographique des anomalies"
          />
        </motion.div>
      </motion.div>
      ) : null}

      {activeSubPage === "transactions" ? (
      <AnomaliesView results={results} />
      ) : null}
    </section>
  );
}
