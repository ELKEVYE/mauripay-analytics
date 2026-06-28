import { useMemo } from "react";
import { BarChart3, Cable, Donut } from "lucide-react";
import { motion } from "framer-motion";
import type { Variants } from "framer-motion";
import Plot from "react-plotly.js";
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
import type { ApiSnapshot } from "../api/client";
import { HourlyHeatmap } from "../components/HourlyHeatmap";

type OperationsAnalysisViewProps = {
  snapshot: ApiSnapshot | null;
};

function entriesToChart(data: Record<string, number>) {
  return Object.entries(data).map(([name, value]) => ({ name, value }));
}

const axisStyle = {
  axisLine: false,
  tickLine: false,
  tick: { fill: "#64748b", fontSize: 11 },
};

const chartGridVariants: Variants = {
  hidden: {},
  visible: {
    transition: {
      delayChildren: 0.08,
      staggerChildren: 0.12,
    },
  },
};

const chartCardVariants: Variants = {
  hidden: { opacity: 0, y: 22, scale: 0.985 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.46, ease: "easeOut" },
  },
};

const chartHover = {
  y: -5,
  boxShadow: "0 24px 55px -34px rgba(15, 23, 42, 0.45)",
  transition: { duration: 0.22, ease: "easeOut" },
} as const;

function formatValue(value: number) {
  return value.toLocaleString("fr-FR");
}

function ChartCardHeader({
  title,
  description,
  icon: Icon,
  tone,
}: {
  title: string;
  description: string;
  icon: typeof BarChart3;
  tone: "blue" | "emerald" | "violet";
}) {
  const toneClasses = {
    blue: "bg-blue-50 text-blue-600",
    emerald: "bg-emerald-50 text-mauri-green",
    violet: "bg-violet-50 text-violet-600",
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

export function OperationsAnalysisView({ snapshot }: OperationsAnalysisViewProps) {
  const typeChart = useMemo(
    () => entriesToChart(snapshot?.stats.by_type ?? {}),
    [snapshot?.stats.by_type],
  );
  const channelChart = useMemo(
    () => entriesToChart(snapshot?.stats.by_channel ?? {}),
    [snapshot?.stats.by_channel],
  );
  const operatorNames = useMemo(
    () => (snapshot?.timeseries.volume_by_operator ?? []).map((item) => item.operator).sort(),
    [snapshot?.timeseries.volume_by_operator],
  );

  return (
    <section
      className="flex flex-col gap-4 lg:h-[calc(100vh-8.5rem)] lg:min-h-[640px]"
      aria-label="Analyse des operations"
    >
      <motion.div
        className="grid flex-1 gap-4 lg:min-h-0 lg:grid-cols-2 lg:grid-rows-2"
        initial="hidden"
        animate="visible"
        variants={chartGridVariants}
      >
        <HourlyHeatmap compact rows={snapshot?.timeseries.hourly_heatmap ?? []} />

        <motion.div
          className="dashboard-card chart-card min-h-[360px] border-blue-100 bg-gradient-to-br from-white via-white to-blue-50/45 lg:min-h-0"
          variants={chartCardVariants}
          whileHover={chartHover}
        >
          <ChartCardHeader
            description="Transactions traitees par operateur"
            icon={BarChart3}
            title="Volume par operateur"
            tone="blue"
          />
          <div className="min-h-0 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                barCategoryGap={10}
                data={operatorNames.map((operator) => {
                  const row = snapshot?.timeseries.volume_by_operator.find((item) => item.operator === operator);
                  return { operator, transactions: row?.transactions ?? 0 };
                })}
                layout="vertical"
                margin={{ top: 4, right: 58, left: 8, bottom: 0 }}
              >
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" horizontal={false} />
                <XAxis type="number" {...axisStyle} />
                <YAxis dataKey="operator" type="category" width={120} {...axisStyle} />
                <Tooltip />
                <Bar
                  animationBegin={260}
                  animationDuration={900}
                  animationEasing="ease-out"
                  dataKey="transactions"
                  fill="#0f766e"
                  isAnimationActive
                  radius={[0, 8, 8, 0]}
                  barSize={14}
                >
                  <LabelList
                    className="fill-slate-600 text-[11px] font-bold"
                    dataKey="transactions"
                    formatter={(value: number) => formatValue(value)}
                    position="right"
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          className="dashboard-card chart-card min-h-[360px] border-violet-100 bg-gradient-to-br from-white via-white to-violet-50/45 lg:min-h-0"
          variants={chartCardVariants}
          whileHover={chartHover}
        >
          <ChartCardHeader
            description="Part des transactions par categorie"
            icon={Donut}
            title="Repartition par type"
            tone="violet"
          />
          <div className="flex min-h-0 flex-1 items-center justify-center">
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
                transition: { duration: 450, easing: "cubic-in-out" },
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
        </motion.div>

        <motion.div
          className="dashboard-card chart-card min-h-[360px] border-teal-100 bg-gradient-to-br from-white via-white to-teal-50/45 lg:min-h-0"
          variants={chartCardVariants}
          whileHover={chartHover}
        >
          <ChartCardHeader
            description="Volume par canal de transaction"
            icon={Cable}
            title="Canaux utilises"
            tone="emerald"
          />
          <div className="min-h-0 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                barCategoryGap={28}
                data={channelChart}
                margin={{ top: 8, right: 24, left: -4, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="channelsGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#059669" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#0f766e" stopOpacity={0.8} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="name" {...axisStyle} />
                <YAxis {...axisStyle} />
                <Tooltip />
                <Bar
                  animationBegin={380}
                  animationDuration={850}
                  animationEasing="ease-out"
                  dataKey="value"
                  fill="url(#channelsGradient)"
                  isAnimationActive
                  radius={[8, 8, 2, 2]}
                  maxBarSize={82}
                >
                  <LabelList
                    className="fill-slate-600 text-[11px] font-bold"
                    dataKey="value"
                    formatter={(value: number) => formatValue(value)}
                    position="top"
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}
