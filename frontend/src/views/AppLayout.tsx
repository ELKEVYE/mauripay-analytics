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
  RefreshCw,
  Table2,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import mauriPayLogo from "../assets/mauripay-logo.svg";

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
    icon: LayoutDashboard,
  },
];

const analysisGroups = [
  {
    label: "Analyse des transactions",
    icon: BarChart3,
    views: ["transactionTemporal", "transactionOperations", "transactionGeography"] as AppView[],
    items: [
      { id: "transactionTemporal" as const, label: "Vue temporelle", icon: Clock3 },
      { id: "transactionOperations" as const, label: "Opérations", icon: BarChart3 },
      { id: "transactionGeography" as const, label: "Géographie", icon: MapPinned },
    ],
  },
  {
    label: "Analyse des anomalies",
    icon: AlertTriangle,
    views: ["anomalyTemporal", "anomalyGeography", "anomalyTransactions"] as AppView[],
    items: [
      { id: "anomalyTemporal" as const, label: "Vue temporelle", icon: Clock3 },
      { id: "anomalyGeography" as const, label: "Géographie", icon: MapPinned },
      { id: "anomalyTransactions" as const, label: "Transactions suspectes", icon: Table2 },
    ],
  },
];

const VIEW_TITLES: Record<AppView, string> = {
  dashboard: "Vue d'ensemble",
  transactionTemporal: "Transactions · Vue temporelle",
  transactionOperations: "Transactions · Opérations",
  transactionGeography: "Transactions · Géographie",
  anomalyTemporal: "Anomalies · Vue temporelle",
  anomalyGeography: "Anomalies · Géographie",
  anomalyTransactions: "Anomalies · Transactions suspectes",
};

function NavRow({
  icon: Icon,
  label,
  active,
  collapsed,
  sub,
  onClick,
}: {
  icon: typeof LayoutDashboard;
  label: string;
  active: boolean;
  collapsed?: boolean;
  sub?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      aria-current={active ? "page" : undefined}
      className={`relative flex w-full items-center gap-3 rounded-lg py-2.5 text-left transition-colors ${
        collapsed ? "justify-center px-2" : sub ? "pl-4 pr-3" : "px-3"
      } ${
        active
          ? "bg-anchor-weak text-anchor"
          : "text-ink-muted hover:bg-canvas hover:text-ink"
      }`}
      onClick={onClick}
      title={collapsed ? label : undefined}
      type="button"
    >
      {active ? (
        <motion.span
          aria-hidden="true"
          className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full bg-anchor"
          layoutId="nav-active"
          transition={{ type: "spring", stiffness: 400, damping: 34 }}
        />
      ) : null}
      <Icon className={`${sub ? "h-4 w-4" : "h-[18px] w-[18px]"} shrink-0`} aria-hidden="true" />
      <span
        className={`min-w-0 truncate ${sub ? "text-[13px]" : "text-sm"} ${
          active ? "font-semibold" : "font-medium"
        } ${collapsed ? "lg:hidden" : ""}`}
      >
        {label}
      </span>
    </button>
  );
}

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
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  function navigate(view: AppView) {
    onNavigate(view);
    setMobileMenuOpen(false);
    setNotificationsOpen(false);
    setApiPanelOpen(false);
  }

  return (
    <div className="app-shell min-h-screen overflow-x-hidden">
      <motion.header
        data-testid="app-header"
        className={`app-header fixed left-0 right-0 top-0 z-40 flex h-[64px] min-w-0 items-center border-b border-hairline border-t-2 border-t-anchor bg-surface px-4 transition-[left] duration-300 ease-in-out sm:px-5 ${
          sidebarCollapsed ? "lg:left-20" : "lg:left-64"
        }`}
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        <button
          aria-label="Ouvrir le menu"
          className="mr-3 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-hairline text-ink-muted transition-colors hover:bg-canvas hover:text-ink lg:hidden"
          onClick={() => setMobileMenuOpen(true)}
          type="button"
        >
          <Menu className="h-5 w-5" />
        </button>

        <button
          aria-label={sidebarCollapsed ? "Agrandir la sidebar" : "Réduire la sidebar"}
          className="mr-3 hidden h-10 w-10 items-center justify-center rounded-lg border border-hairline text-ink-muted transition-colors hover:bg-canvas hover:text-ink lg:inline-flex"
          onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
          type="button"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex min-w-0 items-center gap-2.5 lg:hidden">
          <img src={mauriPayLogo} alt="" className="h-8 w-8 shrink-0" aria-hidden="true" />
          <p className="truncate text-sm font-semibold text-ink">MauriPay Analytics</p>
        </div>

        <p className="hidden min-w-0 truncate text-sm font-semibold text-ink lg:block">
          {VIEW_TITLES[activeView]}
        </p>

        <div className="ml-auto flex min-w-0 items-center gap-1.5 sm:gap-2">
          {datasetName ? (
            <div
              className="hidden max-w-52 items-center gap-2 rounded-lg border border-hairline px-3 py-2 text-ink-muted 2xl:flex"
              title={datasetName}
            >
              <Database className="h-4 w-4 shrink-0 text-anchor" aria-hidden="true" />
              <span className="tnum truncate text-xs font-medium">{datasetName}</span>
            </div>
          ) : null}

          <div className="hidden min-w-[64px] text-right md:block">
            <p className="tnum text-sm font-semibold leading-4 text-ink">
              {now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
            </p>
            <p className="tnum mt-0.5 hidden text-[10px] font-medium text-ink-faint lg:block">
              {now.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" })}
            </p>
          </div>

          <div className="relative">
            <button
              aria-expanded={notificationsOpen}
              aria-label={`${anomalyCount} anomalies détectées`}
              className="relative inline-flex h-10 w-10 items-center justify-center rounded-lg border border-transparent text-ink-muted transition-colors hover:border-hairline hover:bg-canvas hover:text-ink"
              onClick={() => {
                setNotificationsOpen((open) => !open);
                setApiPanelOpen(false);
              }}
              title="Notifications"
              type="button"
            >
              <Bell className="h-[18px] w-[18px]" />
              {anomalyCount > 0 ? (
                <span className="tnum absolute -right-1 -top-1 min-w-[18px] rounded-full bg-alert px-1 text-center text-[10px] font-semibold leading-[18px] text-white ring-2 ring-surface">
                  {anomalyCount > 99 ? "99+" : anomalyCount}
                </span>
              ) : null}
            </button>
            {notificationsOpen ? (
              <div className="app-popover absolute right-0 top-12 w-72 rounded-xl border border-hairline bg-surface p-3 shadow-pop">
                <p className="text-sm font-semibold text-ink">Notifications</p>
                <div className="mt-3 rounded-lg border border-alert/20 bg-alert-weak p-3">
                  <p className="tnum text-sm font-semibold text-alert">
                    {anomalyCount.toLocaleString("fr-FR")} anomalie(s)
                  </p>
                  <p className="mt-1 text-xs text-alert/80">
                    Détectées par le consensus des trois modèles.
                  </p>
                </div>
                <button
                  className="mt-3 w-full rounded-lg bg-anchor px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-anchor-strong"
                  onClick={() => navigate("anomalyTransactions")}
                  type="button"
                >
                  Voir les transactions suspectes
                </button>
              </div>
            ) : null}
          </div>

          <div className="relative">
            <button
              aria-expanded={apiPanelOpen}
              className={`inline-flex h-10 items-center gap-2 rounded-lg border px-3 text-xs font-semibold transition-colors ${
                apiConnected
                  ? "border-hairline text-ink-muted hover:bg-canvas"
                  : "border-alert/25 bg-alert-weak text-alert"
              }`}
              onClick={() => {
                setApiPanelOpen((open) => !open);
                setNotificationsOpen(false);
              }}
              type="button"
            >
              <span
                aria-hidden="true"
                className={`h-2 w-2 rounded-full ${apiConnected ? "bg-anchor" : "bg-alert"}`}
              />
              {apiConnected ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
              <span className="hidden sm:inline">{apiConnected ? "API connectée" : "API indisponible"}</span>
            </button>
            {apiPanelOpen ? (
              <div className="app-popover absolute right-0 top-12 w-72 rounded-xl border border-hairline bg-surface p-3 shadow-pop">
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className={`h-2.5 w-2.5 rounded-full ${apiConnected ? "bg-anchor" : "bg-alert"}`}
                  />
                  <p className="text-sm font-semibold text-ink">
                    {apiConnected ? "Service disponible" : "Connexion interrompue"}
                  </p>
                </div>
                <p className="mt-2 break-all font-mono text-xs text-ink-muted">
                  {import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"}
                </p>
                <button
                  className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-hairline px-3 py-2 text-sm font-semibold text-ink-muted transition-colors hover:bg-canvas"
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
        </div>
      </motion.header>

      <AnimatePresence>
        {mobileMenuOpen ? (
          <motion.button
            aria-label="Fermer le menu"
            className="fixed inset-0 z-40 bg-ink/30 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.16 }}
            onClick={() => setMobileMenuOpen(false)}
            type="button"
          />
        ) : null}
      </AnimatePresence>

      <aside
        data-testid="app-sidebar"
        className={`app-sidebar fixed bottom-0 left-0 top-0 z-50 flex w-64 flex-col border-r border-hairline bg-surface transition-[width,transform] duration-300 ease-in-out lg:translate-x-0 ${
          sidebarCollapsed ? "lg:w-20" : "lg:w-64"
        } ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex h-[64px] shrink-0 items-center gap-3 border-b border-hairline px-4">
          <img src={mauriPayLogo} alt="" className="h-9 w-9 shrink-0" aria-hidden="true" />
          <div className={`min-w-0 flex-1 ${sidebarCollapsed ? "lg:hidden" : ""}`}>
            <p className="truncate text-[15px] font-semibold leading-5 text-ink">
              MauriPay <span className="text-anchor">Analytics</span>
            </p>
            <p className="truncate text-[11px] font-medium text-ink-muted">Supervision Mobile Money</p>
          </div>
          <button
            aria-label="Fermer le menu"
            className="ml-auto inline-flex h-9 w-9 items-center justify-center rounded-lg text-ink-muted hover:bg-canvas lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav
          className="no-scrollbar flex-1 space-y-1 overflow-y-auto px-3 py-4"
          aria-label="Navigation principale"
        >
          <p
            className={`mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-faint ${
              sidebarCollapsed ? "lg:hidden" : ""
            }`}
          >
            Principal
          </p>
          {navigation.map((item) => (
            <NavRow
              key={item.id}
              icon={item.icon}
              label={item.label}
              active={activeView === item.id}
              collapsed={sidebarCollapsed}
              onClick={() => navigate(item.id)}
            />
          ))}

          {analysisGroups.map((group) => {
            const GroupIcon = group.icon;
            const groupActive = group.views.includes(activeView);

            return (
              <div className="pt-4" key={group.label}>
                <div
                  className={`mb-1 flex items-center gap-2.5 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.06em] ${
                    groupActive ? "text-anchor" : "text-ink-faint"
                  } ${sidebarCollapsed ? "lg:justify-center" : ""}`}
                  title={sidebarCollapsed ? group.label : undefined}
                >
                  <GroupIcon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span className={sidebarCollapsed ? "lg:hidden" : ""}>{group.label}</span>
                </div>
                <div className={`space-y-1 ${sidebarCollapsed ? "" : "border-l border-hairline pl-2"}`}>
                  {group.items.map((item) => (
                    <NavRow
                      key={item.id}
                      icon={item.icon}
                      label={item.label}
                      active={activeView === item.id}
                      collapsed={sidebarCollapsed}
                      sub={!sidebarCollapsed}
                      onClick={() => navigate(item.id)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </nav>

        <div
          className={`shrink-0 border-t border-hairline px-4 py-3 ${sidebarCollapsed ? "lg:hidden" : ""}`}
        >
          <button
            className="inline-flex items-center gap-2 text-xs font-medium text-ink-muted transition-colors hover:text-ink disabled:opacity-40"
            disabled={refreshing || !datasetName}
            onClick={onRefresh}
            type="button"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Rafraîchir les données
          </button>
        </div>
      </aside>

      <div
        data-testid="app-content"
        className={`app-content min-h-screen min-w-0 pt-[64px] transition-[padding] duration-300 ease-in-out ${
          sidebarCollapsed ? "lg:pl-20" : "lg:pl-64"
        }`}
      >
        {children}
      </div>
    </div>
  );
}
