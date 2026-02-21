/**
 * FIRE Simulator — Monte Carlo simulation UI with configuration panel,
 * life events editor, results visualization, and sensitivity analysis.
 *
 * Methodology citations:
 * - Bengen (1994): 4% safe withdrawal rate
 * - Trinity Study (1998): success rate analysis
 * - Guyton & Klinger (2006): guardrail withdrawal rules
 * - Kitces (2008+): rising equity glidepath
 */

import { useState } from "react";
import { SimulationConfigPanel } from "./SimulationConfigPanel";
import { LifeEventsEditor } from "./LifeEventsEditor";
import { ResultsVisualization } from "./ResultsVisualization";
import { SensitivityAnalysis } from "./SensitivityAnalysis";
import { useSimulationStore } from "../../stores/simulation";
import { useRunScenario } from "../../hooks/useSimulation";
import type { SimulationResult } from "../../types";

function EmptyState({ nTrials, nYears }: { nTrials: number; nYears: number }) {
  return (
    <div className="bg-card border border-border rounded-lg p-12 text-center">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="mx-auto mb-4 text-muted-foreground/40">
        <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
      </svg>
      <p className="text-muted-foreground">
        Configure your simulation parameters and click{" "}
        <span className="text-primary font-medium">Run Simulation</span> to see results.
      </p>
      <p className="text-xs text-muted-foreground mt-2">
        Uses {nTrials.toLocaleString()} Monte Carlo trials over {nYears} years
        with historical S&amp;P 500 returns.
      </p>
    </div>
  );
}

function LoadingState({ nTrials }: { nTrials: number }) {
  return (
    <div className="bg-card border border-border rounded-lg p-12 text-center">
      <div className="animate-pulse space-y-3">
        <div className="h-4 bg-muted rounded w-1/3 mx-auto" />
        <div className="h-48 bg-muted rounded" />
        <div className="h-4 bg-muted rounded w-2/3 mx-auto" />
      </div>
      <p className="text-sm text-muted-foreground mt-4">
        Running {nTrials.toLocaleString()} Monte Carlo trials...
      </p>
    </div>
  );
}

function TabSwitcher({
  active,
  onSwitch,
}: {
  active: string;
  onSwitch: (tab: "results" | "sensitivity") => void;
}) {
  const tabClass = (tab: string) =>
    `flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
      active === tab
        ? "bg-card text-foreground shadow-sm"
        : "text-muted-foreground hover:text-foreground"
    }`;

  return (
    <div className="flex gap-1 bg-muted p-1 rounded-lg">
      <button onClick={() => onSwitch("results")} className={tabClass("results")}>
        Results
      </button>
      <button onClick={() => onSwitch("sensitivity")} className={tabClass("sensitivity")}>
        Sensitivity Analysis
      </button>
    </div>
  );
}

export function FireSimulator() {
  const { config } = useSimulationStore();
  const scenario = useRunScenario();
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [activeTab, setActiveTab] = useState<"results" | "sensitivity">("results");

  async function handleRun() {
    try {
      const data = await scenario.mutateAsync(config);
      setResult(data);
    } catch { /* handled by mutation error state */ }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground">FIRE Simulator</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Monte Carlo simulation for Financial Independence, Retire Early planning.
        </p>
      </div>
      <div className="flex gap-6">
        <div className="w-80 shrink-0 space-y-4">
          <SimulationConfigPanel onRun={handleRun} isRunning={scenario.isPending} />
          <LifeEventsEditor />
        </div>
        <div className="flex-1 min-w-0 space-y-4">
          {scenario.isError && (
            <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm">
              <p className="font-medium">Simulation failed</p>
              <p className="mt-1">{scenario.error.message}</p>
            </div>
          )}
          {!result && !scenario.isPending && !scenario.isError && (
            <EmptyState nTrials={config.n_trials ?? 10_000} nYears={config.n_years ?? 30} />
          )}
          {scenario.isPending && <LoadingState nTrials={config.n_trials ?? 10_000} />}
          {result && !scenario.isPending && (
            <>
              <TabSwitcher active={activeTab} onSwitch={setActiveTab} />
              {activeTab === "results" && (
                <ResultsVisualization result={result} initialPortfolio={config.initial_portfolio} />
              )}
              {activeTab === "sensitivity" && <SensitivityAnalysis />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
