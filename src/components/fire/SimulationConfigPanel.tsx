/**
 * FIRE simulation configuration panel — input fields for portfolio parameters,
 * withdrawal strategy, and FIRE type presets.
 */

import { useState } from "react";
import { useSimulationStore, FIRE_PRESETS, WITHDRAWAL_STRATEGIES } from "../../stores/simulation";
import type { FIREType, WithdrawalStrategy } from "../../types";

const INPUT_CLASS =
  "w-full px-3 py-2 bg-muted border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary";

function CurrencyField({ label, value, onChange, hint }: {
  label: string; value: number; onChange: (v: number) => void; hint?: string;
}) {
  const [display, setDisplay] = useState(value.toLocaleString("en-US"));
  function handleBlur() {
    const parsed = Number(display.replace(/[^0-9.-]/g, "")) || 0;
    onChange(parsed);
    setDisplay(parsed.toLocaleString("en-US"));
  }
  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-1">{label}</label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
        <input type="text" value={display} onChange={(e) => setDisplay(e.target.value)} onBlur={handleBlur} className={`${INPUT_CLASS} pl-7`} />
      </div>
      {hint && <p className="text-xs text-muted-foreground mt-1">{hint}</p>}
    </div>
  );
}

function NumberField({ label, value, onChange, min, max, step, suffix, hint }: {
  label: string; value: number; onChange: (v: number) => void;
  min?: number; max?: number; step?: number; suffix?: string; hint?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-muted-foreground mb-1">{label}</label>
      <div className="relative">
        <input type="number" value={value} onChange={(e) => onChange(Number(e.target.value))} min={min} max={max} step={step} className={INPUT_CLASS} />
        {suffix && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">{suffix}</span>}
      </div>
      {hint && <p className="text-xs text-muted-foreground mt-1">{hint}</p>}
    </div>
  );
}

function StrategyOption({ strategy, selected, onSelect }: {
  strategy: WithdrawalStrategy; selected: boolean; onSelect: () => void;
}) {
  const info = WITHDRAWAL_STRATEGIES[strategy];
  return (
    <label className={`flex items-start gap-3 p-3 rounded-md border cursor-pointer transition-colors ${selected ? "border-primary bg-primary/5" : "border-border bg-muted hover:border-muted-foreground/30"}`}>
      <input type="radio" name="withdrawal_strategy" value={strategy} checked={selected} onChange={onSelect} className="mt-0.5 accent-primary" />
      <div>
        <p className="text-sm font-medium text-foreground">{info.label}</p>
        <p className="text-xs text-muted-foreground">{info.description}</p>
      </div>
    </label>
  );
}

export function SimulationConfigPanel({ onRun, isRunning }: { onRun: () => void; isRunning: boolean }) {
  const { config, setConfig, resetConfig, applyPreset } = useSimulationStore();
  const withdrawalHint = config.initial_portfolio > 0
    ? `${((config.annual_withdrawal / config.initial_portfolio) * 100).toFixed(1)}% withdrawal rate`
    : undefined;

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Simulation Configuration</h3>
        <button onClick={resetConfig} className="text-xs text-muted-foreground hover:text-foreground transition-colors">Reset defaults</button>
      </div>
      <div>
        <label className="block text-xs font-medium text-muted-foreground mb-2">FIRE Type Preset</label>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(FIRE_PRESETS) as FIREType[]).map((type) => (
            <button key={type} onClick={() => applyPreset(type)} className="px-3 py-1.5 text-xs rounded-md border border-border bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-colors" title={FIRE_PRESETS[type].description}>
              {FIRE_PRESETS[type].label}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <CurrencyField label="Initial Portfolio" value={config.initial_portfolio} onChange={(v) => setConfig({ initial_portfolio: v })} />
        <CurrencyField label="Annual Withdrawal" value={config.annual_withdrawal} onChange={(v) => setConfig({ annual_withdrawal: v })} hint={withdrawalHint} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <NumberField label="Time Horizon" value={config.n_years ?? 30} onChange={(v) => setConfig({ n_years: v })} min={1} max={100} suffix="years" />
        <NumberField label="Inflation Rate" value={(config.inflation_rate ?? 0.03) * 100} onChange={(v) => setConfig({ inflation_rate: v / 100 })} min={0} max={20} step={0.1} suffix="%" />
      </div>
      <NumberField label="Monte Carlo Trials" value={config.n_trials ?? 10_000} onChange={(v) => setConfig({ n_trials: v })} min={100} max={100_000} step={1000} hint="More trials = more accurate but slower. 10,000 is standard." />
      <div>
        <label className="block text-xs font-medium text-muted-foreground mb-2">Withdrawal Strategy</label>
        <div className="space-y-2">
          {(Object.keys(WITHDRAWAL_STRATEGIES) as WithdrawalStrategy[]).map((s) => (
            <StrategyOption key={s} strategy={s} selected={config.withdrawal_strategy === s} onSelect={() => setConfig({ withdrawal_strategy: s })} />
          ))}
        </div>
      </div>
      <button onClick={onRun} disabled={isRunning} className="w-full py-2.5 rounded-md bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
        {isRunning ? "Running Simulation..." : "Run Simulation"}
      </button>
    </div>
  );
}
