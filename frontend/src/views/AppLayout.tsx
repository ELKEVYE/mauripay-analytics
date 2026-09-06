import { useEffect, useState, type ReactNode } from "react";
import { Bell, Database, Menu, RefreshCw, Wifi, WifiOff, X } from "lucide-react";
import { AnimatePresence, LayoutGroup, motion } from "framer-motion";
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

type SubTab = { view: AppView; label: string };
type Section = {
  id: string;
  label: string;
  target: AppView;
  views: AppView[];
  tabs?: SubTab[];
};

const SECTIONS: Section[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    target: "dashboard",
    views: ["dashboard"],
  },
  {
    id: "transactions",
    label: "Transactions",
    target: "transactionTemporal",
    views: ["transactionTemporal", "transactionOperations", "transactionGeography"],
    tabs: [
      { view: "transactionTemporal", label: "Vue temporelle" },
      { view: "transactionOperations", label: "Opérations" },
      { view: "transactionGeography", label: "Géographie" },
    ],
  },
  {
    id: "anomalies",
    label: "Anomalies",
    target: "anomalyTransactions",
    views: ["anomalyTemporal", "anomalyGeography", "anomalyTransactions"],
    tabs: [
      { view: "anomalyTemporal", label: "Vue temporelle" },
      { view: "anomalyGeography", label: "Géographie" },
      { view: "anomalyTransactions", label: "Transactions suspectes" },
    ],
  },
];

function sectionForView(view: AppView): Section {
  return SECTIONS.find((section) => section.views.includes(view)) ?? SECTIONS[0];
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
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [apiPanelOpen, setApiPanelOpen] = useState(false);
  const [now, setNow] = useState(() => new Date());

  const activeSection = sectionForView(activeView);
  const subTabs = activeSection.tabs;

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
    <div className="app-shell flex min-h-screen flex-col overflow-x-hidden">
      <motion.header
        data-testid="app-header"
        className="app-header sticky top-0 z-40 border-b border-hairline border-t-2 border-t-anchor bg-surface/95 backdrop-blur"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        {/* Row 1 — brand, primary nav, controls */}
        <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-4 px-4 md:px-6">
          <button
            aria-label="Ouvrir le menu"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-hairline text-ink-muted transition-colors hover:bg-canvas hover:text-ink lg:hidden"
            onClick={() => setMobileMenuOpen((open) => !open)}
            type="button"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          <div className="flex min-w-0 items-center gap-2.5">
            <img src={mauriPayLogo} alt="" className="h-8 w-8 shrink-0" aria-hidden="true" />
            <p className="truncate text-[15px] font-semibold text-ink">
              MauriPay <span className="text-anchor">Analytics</span>
            </p>
          </div>

          <LayoutGroup id="primary-nav">
            <nav
              className="ml-4 hidden items-center gap-1 lg:flex"
              aria-label="Navigation principale"
            >
              {SECTIONS.map((section) => {
                const active = activeSection.id === section.id;
                return (
                  <button
                    key={section.id}
                    aria-current={active ? "page" : undefined}
                    className={`relative rounded-lg px-3 py-2 text-sm transition-colors ${
                      active ? "font-semibold text-ink" : "font-medium text-ink-muted hover:text-ink"
                    }`}
                    onClick={() => navigate(section.tabs ? section.tabs[0].view : section.target)}
                    type="button"
                  >
                    {section.label}
                    {active ? (
                      <motion.span
                        aria-hidden="true"
                        className="absolute inset-x-2 -bottom-[9px] h-0.5 rounded-full bg-anchor"
                        layoutId="primary-underline"
                        transition={{ type: "spring", stiffness: 420, damping: 34 }}
                      />
                    ) : null}
                  </button>
                );
              })}
            </nav>
          </LayoutGroup>

          <div className="ml-auto flex min-w-0 items-center gap-1.5 sm:gap-2">
            {datasetName ? (
              <div
                className="hidden max-w-48 items-center gap-2 rounded-lg border border-hairline px-2.5 py-1.5 text-ink-muted xl:flex"
                title={datasetName}
              >
                <Database className="h-4 w-4 shrink-0 text-anchor" aria-hidden="true" />
                <span className="tnum truncate text-xs font-medium">{datasetName}</span>
              </div>
            ) : null}

            <p className="tnum mr-1 hidden text-sm font-semibold text-ink md:block">
              {now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
            </p>

            <button
              aria-label="Rafraîchir les données"
              className="hidden h-9 w-9 items-center justify-center rounded-lg border border-hairline text-ink-muted transition-colors hover:bg-canvas hover:text-ink disabled:opacity-40 sm:inline-flex"
              disabled={refreshing || !datasetName}
              onClick={onRefresh}
              type="button"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            </button>

            <div className="relative">
              <button
                aria-expanded={notificationsOpen}
                aria-label={`${anomalyCount} anomalies détectées`}
                className="relative inline-flex h-9 w-9 items-center justify-center rounded-lg border border-transparent text-ink-muted transition-colors hover:border-hairline hover:bg-canvas hover:text-ink"
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
              <AnimatePresence>
                {notificationsOpen ? (
                  <motion.div
                    key="notif-panel"
                    className="absolute right-0 top-11 w-72 rounded-xl border border-hairline bg-surface p-3 shadow-pop"
                    initial={{ opacity: 0, y: -6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -6, scale: 0.98 }}
                    transition={{ duration: 0.15, ease: "easeOut" }}
                  >
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
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>

            <div className="relative">
              <button
                aria-expanded={apiPanelOpen}
                className={`inline-flex h-9 items-center gap-2 rounded-lg border px-2.5 text-xs font-semibold transition-colors ${
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
              <AnimatePresence>
                {apiPanelOpen ? (
                  <motion.div
                    key="api-panel"
                    className="absolute right-0 top-11 w-72 rounded-xl border border-hairline bg-surface p-3 shadow-pop"
                    initial={{ opacity: 0, y: -6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -6, scale: 0.98 }}
                    transition={{ duration: 0.15, ease: "easeOut" }}
                  >
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
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
          </div>
        </div>

        {/* Row 2 — contextual sub-tabs for the active section */}
        <AnimatePresence initial={false}>
          {subTabs ? (
            <motion.div
              key="subtabs"
              className="overflow-hidden border-t border-hairline bg-canvas/60"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
            >
              <LayoutGroup id="subtab-nav">
                <nav
                  className="no-scrollbar mx-auto flex w-full max-w-7xl gap-1 overflow-x-auto px-4 md:px-6"
                  aria-label={`Sous-sections ${activeSection.label}`}
                >
                  {subTabs.map((tab) => {
                    const active = activeView === tab.view;
                    return (
                      <button
                        key={tab.view}
                        aria-current={active ? "page" : undefined}
                        className={`relative whitespace-nowrap px-3 py-2.5 text-[13px] transition-colors ${
                          active ? "font-semibold text-anchor" : "font-medium text-ink-muted hover:text-ink"
                        }`}
                        onClick={() => navigate(tab.view)}
                        type="button"
                      >
                        {tab.label}
                        {active ? (
                          <motion.span
                            aria-hidden="true"
                            className="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-anchor"
                            layoutId="subtab-underline"
                            transition={{ type: "spring", stiffness: 420, damping: 34 }}
                          />
                        ) : null}
                      </button>
                    );
                  })}
                </nav>
              </LayoutGroup>
            </motion.div>
          ) : null}
        </AnimatePresence>

        {/* Mobile menu */}
        <AnimatePresence>
          {mobileMenuOpen ? (
            <motion.div
              key="mobile-menu"
              className="border-t border-hairline bg-surface lg:hidden"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <nav className="space-y-1 px-4 py-3" aria-label="Navigation mobile">
                {SECTIONS.map((section) => (
                  <div key={section.id}>
                    <button
                      className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                        activeSection.id === section.id
                          ? "bg-anchor-weak font-semibold text-anchor"
                          : "font-medium text-ink hover:bg-canvas"
                      }`}
                      onClick={() => navigate(section.tabs ? section.tabs[0].view : section.target)}
                      type="button"
                    >
                      {section.label}
                    </button>
                    {section.tabs ? (
                      <div className="ml-3 mt-1 space-y-1 border-l border-hairline pl-3">
                        {section.tabs.map((tab) => (
                          <button
                            key={tab.view}
                            className={`w-full rounded-lg px-3 py-1.5 text-left text-[13px] transition-colors ${
                              activeView === tab.view
                                ? "font-semibold text-anchor"
                                : "font-medium text-ink-muted hover:bg-canvas hover:text-ink"
                            }`}
                            onClick={() => navigate(tab.view)}
                            type="button"
                          >
                            {tab.label}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
                <button
                  className="mt-2 inline-flex items-center gap-2 px-3 text-xs font-medium text-ink-muted transition-colors hover:text-ink disabled:opacity-40"
                  disabled={refreshing || !datasetName}
                  onClick={onRefresh}
                  type="button"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
                  Rafraîchir les données
                </button>
              </nav>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </motion.header>

      <div data-testid="app-content" className="app-content min-w-0 flex-1">
        {children}
      </div>
    </div>
  );
}
