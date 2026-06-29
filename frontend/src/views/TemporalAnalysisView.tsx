import { AlertTriangle, Banknote, CalendarDays, TrendingUp } from "lucide-react";
import { motion } from "framer-motion";
import type { Variants } from "framer-motion";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ApiSnapshot } from "../api/client";

type TemporalAnalysisViewProps = {
  snapshot: ApiSnapshot | null;
};

type ChartHeaderProps = {
  title: string;
  description: string;
  icon: typeof TrendingUp;
  tone: "green" | "orange" | "red" | "violet";
};

const headerToneClasses = {
  green: "bg-emerald-50 text-mauri-green",
  orange: "bg-orange-50 text-orange-600",
  red: "bg-rose-50 text-rose-600",
  violet: "bg-violet-50 text-violet-600",
};

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

function ChartHeader({ title, description, icon: Icon, tone }: ChartHeaderProps) {
  return (
    <header className="mb-3 flex items-start gap-3">
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded ${headerToneClasses[tone]}`}>
        <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
      </span>
      <div className="flex min-w-0 items-start gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-extrabold text-ink">{title}</h2>
          <p className="mt-0.5 text-xs font-medium text-slate-500">{description}</p>
        </div>
      </div>
    </header>
  );
}

export function TemporalAnalysisView({ snapshot }: TemporalAnalysisViewProps) {
  const transactionsByDay = snapshot?.timeseries.transactions_by_day ?? [];
  const amountsByDay = snapshot?.timeseries.amounts_by_day ?? [];
  const anomaliesByWeek = snapshot?.timeseries.anomalies_by_week ?? [];

  return (
    <section
      className="flex flex-col gap-4"
      aria-label="Analyse temporelle"
    >
      <motion.div
        className="grid gap-4 md:grid-cols-2"
        initial="hidden"
        animate="visible"
        variants={chartGridVariants}
      >
        <motion.div
          className="dashboard-card chart-card min-h-[290px] border-slate-200 bg-white"
          variants={chartCardVariants}
          whileHover={chartHover}
        >
          <ChartHeader
            description="Evolution quotidienne des transactions"
            icon={TrendingUp}
            title="Transactions par jour"
            tone="green"
          />
          <div className="min-h-[190px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={transactionsByDay} margin={{ top: 8, right: 14, left: -8, bottom: 0 }}>
                <defs>
                  <linearGradient id="transactionsGradient" x1="0" x2="0" y1="0" y2="1">
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
                  animationBegin={180}
                  animationDuration={950}
                  animationEasing="ease-out"
                  dataKey="transactions"
                  dot={{ r: 2, strokeWidth: 1 }}
                  fill="url(#transactionsGradient)"
                  isAnimationActive
                  stroke="#059669"
                  strokeWidth={2.5}
                  type="monotone"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          className="dashboard-card chart-card min-h-[290px] border-slate-200 bg-white"
          variants={chartCardVariants}
          whileHover={chartHover}
        >
          <ChartHeader
            description="Montants observes par jour"
            icon={Banknote}
            title="Montants par jour"
            tone="orange"
          />
          <div className="min-h-[190px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={amountsByDay} margin={{ top: 8, right: 14, left: 5, bottom: 0 }}>
                <defs>
                  <linearGradient id="amountsGradient" x1="0" x2="0" y1="0" y2="1">
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
                  animationBegin={260}
                  animationDuration={1000}
                  animationEasing="ease-out"
                  dataKey="total_amount"
                  dot={{ r: 2, strokeWidth: 1 }}
                  fill="url(#amountsGradient)"
                  isAnimationActive
                  stroke="#f59e0b"
                  strokeWidth={2.5}
                  type="monotone"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          className="dashboard-card chart-card min-h-[290px] border-slate-200 bg-white"
          variants={chartCardVariants}
          whileHover={chartHover}
        >
          <ChartHeader
            description="Repartition horaire des anomalies"
            icon={AlertTriangle}
            title="Anomalies par heure"
            tone="red"
          />
          <div className="min-h-[190px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={snapshot?.timeseries.anomalies_by_hour ?? []}
                margin={{ top: 8, right: 14, left: -8, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="hourlyAnomaliesGradient" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#e11d48" stopOpacity={0.95} />
                    <stop offset="100%" stopColor="#fb7185" stopOpacity={0.65} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="hour" {...axisStyle} />
                <YAxis {...axisStyle} />
                <Tooltip />
                <Bar
                  animationBegin={340}
                  animationDuration={850}
                  animationEasing="ease-out"
                  dataKey="anomalies"
                  fill="url(#hourlyAnomaliesGradient)"
                  isAnimationActive
                  radius={[6, 6, 2, 2]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div
          className="dashboard-card chart-card min-h-[290px] border-slate-200 bg-white"
          variants={chartCardVariants}
          whileHover={chartHover}
        >
          <ChartHeader
            description="Evolution hebdomadaire des anomalies"
            icon={CalendarDays}
            title="Anomalies par semaine"
            tone="violet"
          />
          <div className="min-h-[190px] flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={anomaliesByWeek}
                margin={{ top: 8, right: 14, left: -8, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="weeklyAnomaliesGradient" x1="0" x2="0" y1="0" y2="1">
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
                  animationBegin={420}
                  animationDuration={1000}
                  animationEasing="ease-out"
                  dataKey="anomalies"
                  dot={{ r: 2, strokeWidth: 1 }}
                  fill="url(#weeklyAnomaliesGradient)"
                  isAnimationActive
                  stroke="#dc2626"
                  strokeWidth={2.5}
                  type="monotone"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}
