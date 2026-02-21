/**
 * Root application layout — sidebar navigation + content area.
 */

import { Sidebar } from "./components/common/Sidebar";
import { PortfolioDashboard } from "./components/portfolio/PortfolioDashboard";
import { FireSimulator } from "./components/fire/FireSimulator";
import { MarketDashboard } from "./components/market/MarketDashboard";
import { SettingsPage } from "./components/settings/SettingsPage";
import { useUIStore } from "./stores/ui";

function MainContent() {
  const activeView = useUIStore((s) => s.activeView);

  switch (activeView) {
    case "portfolio":
      return <PortfolioDashboard />;
    case "fire":
      return <FireSimulator />;
    case "market":
      return <MarketDashboard />;
    case "settings":
      return <SettingsPage />;
  }
}

export function App() {
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        <MainContent />
      </main>
    </div>
  );
}
