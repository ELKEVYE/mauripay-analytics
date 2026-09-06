import { useMemo } from "react";
import { AlertTriangle, MapPinned, TrendingUp } from "lucide-react";
import { motion } from "framer-motion";
import type { Variants } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ApiSnapshot, GeoWilaya } from "../api/client";
import { DataTable } from "../components/DataTable";
import { GeoMap } from "../components/GeoMap";

type GeographicAnalysisViewProps = {
  snapshot: ApiSnapshot | null;
};

const axisStyle = {
  axisLine: false,
  tickLine: false,
  tick: { fill: "#64748b", fontSize: 11 },
};

const geoGridVariants: Variants = {
  hidden: {},
  visible: {
    transition: {
      delayChildren: 0.08,
      staggerChildren: 0.12,
    },
  },
};

const geoCardVariants: Variants = {
  hidden: { opacity: 0, y: 22, scale: 0.985 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.46, ease: "easeOut" },
  },
};

const geoCardHover = {
  y: -5,
  boxShadow: "0 24px 55px -34px rgba(15, 23, 42, 0.45)",
  transition: { duration: 0.22, ease: "easeOut" },
} as const;

function formatNumber(value: number) {
  return new Intl.NumberFormat("fr-FR").format(Math.round(value));
}

function formatAmount(value: number) {
  return `${formatNumber(value)} MRU`;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)} %`;
}

function topWilayas(wilayas: GeoWilaya[]) {
  return [...wilayas].sort((a, b) => b.transactions - a.transactions).slice(0, 8);
}

function topAnomalyWilayas(wilayas: GeoWilaya[]) {
  return [...wilayas].sort((a, b) => b.anomalies_count - a.anomalies_count).slice(0, 8);
}

function rankedWilayas(wilayas: GeoWilaya[]) {
  return [...wilayas].sort((a, b) => {
    const anomalyDiff = b.anomalies_count - a.anomalies_count;
    if (anomalyDiff !== 0) return anomalyDiff;
    return b.transactions - a.transactions;
  });
}

function ChartCardHeader({
  title,
  description,
  icon: Icon,
  tone,
}: {
  title: string;
  description: string;
  icon: typeof TrendingUp;
  tone: "green" | "red";
}) {
  const toneClasses = {
    green: "bg-emerald-50 text-mauri-green",
    red: "bg-rose-50 text-rose-600",
  };

  return (
    <header className="mb-3 flex items-start gap-3">
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded ${toneClasses[tone]}`}>
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

export function GeographicAnalysisView({ snapshot }: GeographicAnalysisViewProps) {
  const wilayas = useMemo(
    () => topWilayas(snapshot?.geo.wilayas ?? []),
    [snapshot?.geo.wilayas],
  );
  const anomalyWilayas = useMemo(
    () => topAnomalyWilayas(snapshot?.geo.wilayas ?? []),
    [snapshot?.geo.wilayas],
  );
  const tableWilayas = useMemo(
    () => rankedWilayas(snapshot?.geo.wilayas ?? []),
    [snapshot?.geo.wilayas],
  );

  return (
    <section
      className="flex flex-col gap-4 lg:h-[calc(100vh-12rem)] lg:min-h-[570px]"
      aria-label="Analyse geographique"
    >
      <motion.div
        className="grid flex-1 gap-4 lg:min-h-0 lg:grid-cols-2 lg:grid-rows-2"
        initial="hidden"
        animate="visible"
        variants={geoGridVariants}
      >
        <motion.div
          className="dashboard-card chart-card min-h-[335px] border-emerald-100 bg-gradient-to-br from-white via-white to-emerald-50/40 lg:min-h-0"
          variants={geoCardVariants}
          whileHover={geoCardHover}
        >
          <ChartCardHeader
            description="Wilayas avec le plus grand volume"
            icon={TrendingUp}
            title="Transactions par wilaya"
            tone="green"
          />
          <div className="min-h-0 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                barCategoryGap={10}
                data={wilayas}
                layout="vertical"
                margin={{ top: 4, right: 62, left: 8, bottom: 0 }}
              >
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" horizontal={false} />
                <XAxis type="number" {...axisStyle} />
                <YAxis dataKey="wilaya" type="category" width={132} {...axisStyle} />
                <Tooltip formatter={(value) => formatNumber(Number(value))} />
                <Bar
                  animationBegin={180}
                  animationDuration={900}
                  animationEasing="ease-out"
                  dataKey="transactions"
                  fill="#4338ca"
                  isAnimationActive
                  radius={[0, 8, 8, 0]}
                  barSize={14}
                >
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
        </motion.div>

        <motion.div
          className="dashboard-card chart-card min-h-[335px] border-rose-100 bg-gradient-to-br from-white via-white to-rose-50/45 lg:min-h-0"
          variants={geoCardVariants}
          whileHover={geoCardHover}
        >
          <ChartCardHeader
            description="Zones avec le plus de signalements"
            icon={AlertTriangle}
            title="Top wilayas par anomalies"
            tone="red"
          />
          <div className="min-h-0 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                barCategoryGap={10}
                data={anomalyWilayas}
                layout="vertical"
                margin={{ top: 4, right: 50, left: 8, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="geoAnomalyGradient" x1="0" x2="1" y1="0" y2="0">
                    <stop offset="0%" stopColor="#be123c" stopOpacity={0.88} />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity={0.95} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" horizontal={false} />
                <XAxis type="number" {...axisStyle} />
                <YAxis dataKey="wilaya" type="category" width={132} {...axisStyle} />
                <Tooltip formatter={(value) => formatNumber(Number(value))} />
                <Bar
                  animationBegin={300}
                  animationDuration={900}
                  animationEasing="ease-out"
                  dataKey="anomalies_count"
                  fill="url(#geoAnomalyGradient)"
                  isAnimationActive
                  radius={[0, 8, 8, 0]}
                  barSize={14}
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

        <motion.div variants={geoCardVariants} whileHover={geoCardHover}>
          <GeoMap compact wilayas={snapshot?.geo.wilayas ?? []} />
        </motion.div>
        <motion.div variants={geoCardVariants} whileHover={geoCardHover}>
          <DataTable
            compact
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
                key: "anomalies_count",
                label: "Anomalies",
                render: (row) => <AnomalyBadge value={Number(row.anomalies_count)} />,
              },
              {
                key: "failure_rate",
                label: "Taux d'echec",
                render: (row) => <FailureBadge value={Number(row.failure_rate)} />,
              },
            ]}
            rows={tableWilayas}
            tone="blue"
            title="Classement geographique des wilayas"
          />
        </motion.div>
      </motion.div>
    </section>
  );
}
