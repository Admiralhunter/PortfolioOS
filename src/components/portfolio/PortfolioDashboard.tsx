/**
 * Portfolio dashboard — main view combining accounts, holdings,
 * allocation chart, net worth summary, CSV import, and net worth tracker.
 */

import { AccountsList } from "./AccountsList";
import { HoldingsTable } from "./HoldingsTable";
import { AllocationChart } from "./AllocationChart";
import { NetWorthCard } from "./NetWorthCard";
import { CSVImport } from "./CSVImport";
import { NetWorthChart } from "./NetWorthChart";

export function PortfolioDashboard() {
  return (
    <div className="flex gap-6 h-full">
      {/* Left panel — accounts list + import */}
      <div className="w-64 shrink-0 space-y-6">
        <AccountsList />
        <CSVImport />
      </div>

      {/* Main content */}
      <div className="flex-1 space-y-6 min-w-0">
        <NetWorthCard />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-card border border-border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">Holdings</h3>
            <HoldingsTable />
          </div>

          <div className="bg-card border border-border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">Asset Allocation</h3>
            <AllocationChart />
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-semibold text-foreground mb-3">Net Worth History</h3>
          <NetWorthChart />
        </div>
      </div>
    </div>
  );
}
