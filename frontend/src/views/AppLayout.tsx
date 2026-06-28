import { useEffect, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  BarChart3,
  Bell,
  Clock3,
  Database,
  LayoutDashboard,
  MapPinned,
  Menu,
  Moon,
  RefreshCw,
  Sun,
  Table2,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import type { Variants } from "framer-motion";
import mauriPayLogo from "../assets/logo mauripay-analytics.png";

export type AppView =
  | "dashboard"
  | "transactionTemporal"
  | "transactionOperations"
  | "transactionGeography"
  | "anomalyTemporal"
  | "anomalyGeography"
  | "anomalyTransactions";

type AppLayoutProps = {
  activeView: AppView;
  anomalyCount: number;
  apiConnected: boolean;
  children: ReactNode;
  datasetName: string;
  onReconnect: () => void;
  onRefresh: () => void;
  onNavigate: (view: AppView) => void;
  refreshing: boolean;
};

const navigation = [
  {
    id: "dashboard" as const,
    label: "Dashboard",
    description: "Vue d'ensemble",
    icon: LayoutDashboard,
  },
];

const analysisGroups = [
  {
    label: "Analyse des transactions",
    icon: BarChart3,
    views: ["transactionTemporal", "transactionOperations", "transactionGeography"] as AppView[],
    items: [
      {
        id: "transactionTemporal" as const,
        label: "Vue temporelle",
        description: "Transactions et montants",
        icon: Clock3,
      },
      {
        id: "transactionOperations" as const,
        label: "Operations",
        description: "Heures, operateurs, types, canaux",
        icon: BarChart3,
      },
      {
        id: "transactionGeography" as const,
        label: "Geographie",
        description: "Wilayas, carte et volumes",
        icon: MapPinned,
      },
    ],
  },
  {
    label: "Analyse des anomalies",
    icon: AlertTriangle,
    views: ["anomalyTemporal", "anomalyGeography", "anomalyTransactions"] as AppView[],
    items: [
      {
        id: "anomalyTemporal" as const,
        label: "Vue temporelle",
        description: "Heures et semaines",
        icon: Clock3,
      },
      {
        id: "anomalyGeography" as const,
        label: "Geographie",
        description: "Wilayas les plus risquees",
        icon: MapPinned,
      },
      {
        id: "anomalyTransactions" as const,
        label: "Transactions suspectes",
        description: "Liste detaillee des alertes",
        icon: Table2,
      },
    ],
  },
];

const sidebarVariants: Variants = {
  hidden: { opacity: 0, x: -30 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      delayChildren: 0.12,
      duration: 0.55,
      ease: "easeOut",
      staggerChildren: 0.055,
    },
  },
};

const sidebarItemVariants: Variants = {
  hidden: { opacity: 0, x: -12 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.32, ease: "easeOut" },
  },
};

const sidebarActiveVariants: Variants = {
  inactive: { scale: 1 },
  active: {
    scale: [0.98, 1.015, 1],
    transition: { duration: 0.34, ease: "easeOut" },
  },
};


export function AppLayout({
  activeView,
  anomalyCount,
  apiConnected,
  children,
  datasetName,
  onReconnect,
  onRefresh,
  onNavigate,
  refreshing,
}: AppLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [apiPanelOpen, setApiPanelOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const storedTheme = window.localStorage.getItem("mauripay-theme");
    if (storedTheme === "dark") setDarkMode(true);
  }, []);

  function toggleTheme() {
    setDarkMode((current) => {
      const next = !current;
      window.localStorage.setItem("mauripay-theme", next ? "dark" : "light");
      return next;
    });
  }

  function navigate(view: AppView) {
    onNavigate(view);
    setMobileMenuOpen(false);
    setNotificationsOpen(false);
  }

  return (
    <div className={`app-shell min-h-screen overflow-x-hidden ${darkMode ? "app-dark" : ""}`}>
      <motion.header
        data-testid="app-header"
        className={`app-header fixed left-0 right-0 top-0 z-40 flex h-[70px] min-w-0 items-center border-b border-slate-200/75 bg-white/95 px-4 shadow-[0_12px_34px_-30px_rgba(15,23,42,0.55)] backdrop-blur-xl transition-[left] duration-300 ease-in-out sm:px-5 ${
          sidebarCollapsed ? "lg:left-20" : "lg:left-64"
        }`}
        initial={{ opacity: 0, y: -14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.42, ease: "easeOut" }}
      >
        <motion.button
          aria-label="Ouvrir le menu"
          className="mr-3 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-emerald-50 hover:text-mauri-green hover:shadow-md lg:hidden"
          whileHover={{ scale: 1.04, y: -2 }}
          whileTap={{ scale: 0.96 }}
          onClick={() => setMobileMenuOpen(true)}
          type="button"
        >
          <Menu className="h-5 w-5" />
        </motion.button>

        <motion.button
          aria-label={sidebarCollapsed ? "Agrandir la sidebar" : "Réduire la sidebar"}
          className="mr-3 hidden h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-200 hover:bg-emerald-50 hover:text-mauri-green hover:shadow-md lg:inline-flex"
          whileHover={{ scale: 1.04, y: -2 }}
          whileTap={{ scale: 0.96 }}
          onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
          title={sidebarCollapsed ? "Agrandir la sidebar" : "Réduire la sidebar"}
          type="button"
        >
          <Menu className="h-5 w-5" />
        </motion.button>

        <motion.div className="flex min-w-0 items-center gap-3 lg:hidden" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.08, duration: 0.32, ease: "easeOut" }}>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-white shadow-[0_14px_28px_-18px_rgba(5,150,105,0.8)] ring-1 ring-emerald-100">
            <img src={mauriPayLogo} alt="" className="h-8 w-8" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-ink">MauriPay Analytics</p>
            <p className="hidden text-xs text-slate-500 sm:block">Supervision Mobile Money</p>
          </div>
        </motion.div>

        <motion.div className="ml-auto flex min-w-0 items-center gap-1.5 rounded-2xl border border-slate-100 bg-slate-50/55 px-2 py-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)] sm:gap-2" initial={{ opacity: 0, x: 18, scale: 0.98 }} animate={{ opacity: 1, x: 0, scale: 1 }} transition={{ delay: 0.12, duration: 0.42, ease: "easeOut" }}>
          {datasetName ? (
            <div
              className="hidden max-w-48 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-slate-600 shadow-sm 2xl:flex"
              title={datasetName}
            >
              <Database className="h-4 w-4 shrink-0 text-mauri-green" aria-hidden="true" />
              <span className="truncate text-xs font-medium">{datasetName}</span>
            </div>
          ) : null}

          <div className="hidden min-w-[76px] text-right md:block">
            <p className="text-sm font-extrabold leading-4 text-slate-700">
              {now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
            </p>
            <p className="mt-0.5 hidden text-[10px] font-semibold text-slate-400 lg:block">
              {now.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })}
            </p>
          </div>

          <div className="relative">
            <motion.button
              aria-expanded={notificationsOpen}
              aria-label={`${anomalyCount} anomalies détectées`}
              className="relative inline-flex h-10 w-10 items-center justify-center rounded-xl border border-transparent text-slate-500 transition hover:-translate-y-0.5 hover:border-rose-100 hover:bg-white hover:text-rose-600 hover:shadow-md"
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.94 }}
              onClick={() => {
                setNotificationsOpen((open) => !open);
                setApiPanelOpen(false);
              }}
              title="Notifications"
              type="button"
            >
              <motion.span animate={anomalyCount > 0 ? { rotate: [0, -8, 8, 0] } : { rotate: 0 }} transition={{ duration: 1.8, repeat: anomalyCount > 0 ? Infinity : 0, repeatDelay: 5 }}><Bell className="h-4 w-4" /></motion.span>
              {anomalyCount > 0 ? (
                <motion.span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-rose-600 px-1.5 text-center text-[10px] font-black leading-5 text-white ring-2 ring-white" initial={{ opacity: 0, scale: 0.65 }} animate={{ opacity: 1, scale: [1, 1.08, 1] }} transition={{ duration: 1.8, repeat: Infinity, repeatDelay: 3 }}>
                  {anomalyCount > 99 ? "99+" : anomalyCount}
                </motion.span>
              ) : null}
            </motion.button>
            {notificationsOpen ? (
              <div className="app-popover absolute right-0 top-11 w-72 rounded border border-slate-200 bg-white p-3 shadow-[0_24px_58px_-28px_rgba(15,23,42,0.55)]">
                <p className="text-sm font-semibold text-ink">Notifications</p>
                <div className="mt-3 rounded bg-rose-50 p-3">
                  <p className="text-sm font-semibold text-rose-700">
                    {anomalyCount.toLocaleString("fr-FR")} anomalie(s)
                  </p>
                  <p className="mt-1 text-xs text-rose-600">
                    Détectées par le consensus des modèles.
                  </p>
                </div>
                <button
                  className="mt-3 w-full rounded bg-mauri-green px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
                  onClick={() => navigate("anomalyTransactions")}
                  type="button"
                >
                  Voir les anomalies
                </button>
              </div>
            ) : null}
          </div>

          <div className="relative">
            <motion.button
              aria-expanded={apiPanelOpen}
              className={`inline-flex h-10 items-center gap-2 rounded-xl border px-3 text-xs font-extrabold shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
                apiConnected
                  ? "border-emerald-100 bg-emerald-50 text-mauri-green"
                  : "border-red-100 bg-red-50 text-red-600"
              }`}
              whileHover={{ scale: 1.03, y: -2 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => {
                setApiPanelOpen((open) => !open);
                setNotificationsOpen(false);
              }}
              type="button"
            >
              <motion.span className={`h-2 w-2 rounded-full ${apiConnected ? "bg-emerald-500 shadow-[0_0_0_4px_rgba(16,185,129,0.14)]" : "bg-red-500"}`} animate={apiConnected ? { scale: [1, 1.35, 1] } : { scale: 1 }} transition={{ duration: 1.6, repeat: apiConnected ? Infinity : 0, repeatDelay: 1.2 }} />
              {apiConnected ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
              <span className="hidden sm:inline">{apiConnected ? "API connectée" : "API indisponible"}</span>
            </motion.button>
            {apiPanelOpen ? (
              <div className="app-popover absolute right-0 top-11 w-72 rounded border border-slate-200 bg-white p-3 shadow-[0_24px_58px_-28px_rgba(15,23,42,0.55)]">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${apiConnected ? "bg-emerald-500" : "bg-red-500"}`} />
                  <p className="text-sm font-semibold text-ink">
                    {apiConnected ? "Service disponible" : "Connexion interrompue"}
                  </p>
                </div>
                <p className="mt-2 break-all text-xs text-slate-500">
                  {import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"}
                </p>
                <button
                  className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                  disabled={refreshing}
                  onClick={onReconnect}
                  type="button"
                >
                  <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                  Tester la connexion
                </button>
              </div>
            ) : null}
          </div>

          <motion.button
            aria-label={darkMode ? "Activer le mode clair" : "Activer le mode sombre"}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-transparent text-slate-500 transition hover:-translate-y-0.5 hover:border-slate-200 hover:bg-white hover:text-ink hover:shadow-md"
            whileHover={{ rotate: darkMode ? -10 : 10, scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.94 }}
            onClick={toggleTheme}
            title={darkMode ? "Mode clair" : "Mode sombre"}
            type="button"
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </motion.button>

        </motion.div>
      </motion.header>

      <AnimatePresence>
        {mobileMenuOpen ? (
          <motion.button
            aria-label="Fermer le menu"
            className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setMobileMenuOpen(false)}
            type="button"
          />
        ) : null}
      </AnimatePresence>

      <motion.aside
        data-testid="app-sidebar"
        className={`app-sidebar fixed bottom-0 left-0 top-0 z-50 flex w-64 flex-col overflow-hidden bg-gradient-to-b from-[#064e3b] via-[#065f46] to-[#043b2f] text-white shadow-[10px_0_34px_-28px_rgba(15,23,42,0.72)] transition-[width,transform] duration-300 ease-in-out lg:z-50 lg:translate-x-0 ${
          sidebarCollapsed ? "lg:w-20" : "lg:w-64"
        } ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        initial="hidden"
        animate="visible"
        variants={sidebarVariants}
      >
        <motion.div
          className="flex h-[76px] shrink-0 items-center gap-3 border-b border-white/10 px-4"
          variants={sidebarItemVariants}
        >
          <motion.div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white shadow-[0_12px_24px_-18px_rgba(0,0,0,0.75)] ring-1 ring-white/50"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{
              boxShadow: "0 18px 30px -20px rgba(16, 185, 129, 0.85)",
              y: -2,
            }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            <img src={mauriPayLogo} alt="" className="h-9 w-9" aria-hidden="true" />
          </motion.div>
          <div className={`min-w-0 flex-1 ${sidebarCollapsed ? "lg:hidden" : ""}`}>
            <p className="truncate text-[16px] font-black leading-5 text-white">MauriPay Analytics</p>
            <p className="mt-0.5 truncate text-xs font-semibold text-emerald-200/90">Supervision Mobile Money</p>
          </div>
          <button
            aria-label="Fermer le menu"
            className="ml-auto inline-flex h-9 w-9 items-center justify-center rounded text-emerald-100 hover:bg-white/10 lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </motion.div>

        <motion.nav
          className="no-scrollbar flex-1 space-y-2 overflow-y-auto px-3 py-5"
          aria-label="Navigation principale"
          variants={sidebarVariants}
        >
          <motion.p
            className={`mb-3 px-3 text-[10px] font-black uppercase tracking-[0.08em] text-emerald-300/80 ${sidebarCollapsed ? "lg:hidden" : ""}`}
            variants={sidebarItemVariants}
          >
            Principal
          </motion.p>
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = activeView === item.id;

            return (
              <motion.div key={item.id} variants={sidebarItemVariants}>
                <motion.button
                  aria-current={active ? "page" : undefined}
                  className={`relative flex h-12 items-center gap-3 px-3 text-left transition-all duration-200 ${
                    sidebarCollapsed ? "lg:justify-center" : ""
                  } ${
                    active
                      ? `${sidebarCollapsed ? "" : "active-nav-cut"} z-10 rounded-l-[999px] rounded-r-[28px] bg-white text-emerald-900 shadow-[0_14px_30px_-24px_rgba(15,23,42,0.6)] ${
                          sidebarCollapsed ? "w-full" : "w-[calc(100%+0.75rem)]"
                        }`
                      : "w-full rounded-xl text-emerald-50 hover:translate-x-1 hover:bg-white/10 hover:text-white"
                  }`}
                  animate={active ? "active" : "inactive"}
                  onClick={() => navigate(item.id)}
                  title={sidebarCollapsed ? item.label : undefined}
                  type="button"
                  variants={sidebarActiveVariants}
                  whileHover={active ? { y: -1 } : { x: 4 }}
                >
                  {active ? (
                    <motion.span
                      className="absolute right-3 h-2 w-2 rounded-full bg-mauri-green"
                      layoutId="sidebar-active-dot"
                      transition={{ duration: 0.25, ease: "easeOut" }}
                    />
                  ) : null}
                  <span>
                    <Icon className={`h-5 w-5 shrink-0 ${active ? "text-mauri-green" : "text-emerald-100"}`} aria-hidden="true" />
                  </span>
                  <span className={`min-w-0 ${sidebarCollapsed ? "lg:hidden" : ""}`}>
                    <span className="block text-sm font-extrabold leading-none">{item.label}</span>
                  </span>
                </motion.button>
              </motion.div>
            );
          })}

          <motion.p
            className={`mb-3 mt-8 px-3 text-[10px] font-black uppercase tracking-[0.08em] text-emerald-300/80 ${sidebarCollapsed ? "lg:hidden" : ""}`}
            variants={sidebarItemVariants}
          >
            Analyses
          </motion.p>
          {analysisGroups.map((group) => {
            const GroupIcon = group.icon;
            const groupActive = group.views.includes(activeView);

            return (
              <motion.div className="space-y-1.5" key={group.label} variants={sidebarItemVariants}>
                <motion.div
                  className={`flex h-11 items-center gap-3 rounded-xl px-3 text-sm font-extrabold ${
                    groupActive ? "bg-white/10 text-white" : "text-emerald-100"
                  } ${sidebarCollapsed ? "lg:justify-center" : ""}`}
                  title={sidebarCollapsed ? group.label : undefined}
                  whileHover={{ backgroundColor: "rgba(255, 255, 255, 0.12)", x: 3 }}
                  transition={{ duration: 0.2 }}
                >
                  <span>
                    <GroupIcon className="h-5 w-5 shrink-0 text-emerald-100" aria-hidden="true" />
                  </span>
                  <span className={`${sidebarCollapsed ? "lg:hidden" : ""}`}>{group.label}</span>
                </motion.div>
                <motion.div
                  className={`space-y-1 pl-4 ${sidebarCollapsed ? "lg:hidden" : ""}`}
                  variants={sidebarVariants}
                >
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const active = activeView === item.id;

                    return (
                      <motion.button
                        aria-current={active ? "page" : undefined}
                        className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left transition-all duration-200 ${
                          active
                            ? "bg-white text-emerald-900 shadow-[0_12px_26px_-22px_rgba(15,23,42,0.65)]"
                            : "text-emerald-100/85 hover:translate-x-1 hover:bg-white/10 hover:text-white"
                        }`}
                        animate={active ? "active" : "inactive"}
                        key={item.id}
                        onClick={() => navigate(item.id)}
                        type="button"
                        variants={sidebarActiveVariants}
                        whileHover={active ? { y: -1 } : { x: 4 }}
                      >
                        {active ? (
                          <motion.span
                            className="h-1.5 w-1.5 shrink-0 rounded-full bg-mauri-green"
                            layoutId="sidebar-active-subdot"
                            transition={{ duration: 0.22, ease: "easeOut" }}
                          />
                        ) : null}
                        <span>
                          <Icon className={`h-[18px] w-[18px] shrink-0 ${active ? "text-mauri-green" : "text-emerald-100/80"}`} aria-hidden="true" />
                        </span>
                        <span className="min-w-0">
                          <span className="block text-xs font-extrabold leading-4">{item.label}</span>
                          <span className={`block truncate text-[10px] font-semibold leading-4 ${active ? "text-emerald-700" : "text-emerald-200/70"}`}>
                            {item.description}
                          </span>
                        </span>
                      </motion.button>
                    );
                  })}
                </motion.div>
              </motion.div>
            );
          })}
        </motion.nav>

      </motion.aside>

      <div
        data-testid="app-content"
        className={`app-content min-h-screen min-w-0 pt-[70px] transition-[padding] duration-300 ease-in-out ${
          sidebarCollapsed ? "lg:pl-20" : "lg:pl-64"
        }`}
      >
        {children}
      </div>
    </div>
  );
}





