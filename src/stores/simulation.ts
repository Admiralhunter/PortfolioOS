/**
 * Simulation state store — current simulation and scenario configuration.
 *
 * Manages FIRE simulation parameters, withdrawal strategies, life events,
 * and FIRE type presets. Persists config across view switches.
 */

import { create } from "zustand";
import type {
  ScenarioConfig,
  LifeEvent,
  WithdrawalStrategy,
  FIREType,
} from "../types";

/** Historical S&P 500 annual real returns (1928-2023) for bootstrap sampling. */
const HISTORICAL_RETURNS = [
  0.4381, -0.0830, -0.2512, -0.4384, -0.0864, 0.4998, -0.0119, 0.4674,
  0.3194, -0.3534, 0.2928, -0.0110, -0.1067, -0.1277, 0.1942, 0.2551,
  0.1928, 0.3572, -0.0810, 0.0570, 0.0518, 0.1831, 0.3081, 0.2389,
  0.1811, -0.0121, 0.5256, 0.3262, 0.0744, -0.1046, 0.4372, 0.1206,
  0.0034, 0.2664, -0.0881, 0.2261, 0.1642, 0.1244, -0.0998, 0.2380,
  0.1081, -0.0366, 0.1494, -0.1731, -0.2997, 0.3146, 0.2431, -0.0718,
  0.0656, 0.1844, 0.3242, -0.0491, 0.2155, 0.2256, 0.0627, 0.3173,
  0.1867, 0.0525, 0.1661, 0.3169, -0.0310, 0.3047, 0.0762, 0.1008,
  0.0132, 0.3758, 0.2296, 0.3336, 0.2858, 0.2104, -0.0910, -0.1189,
  -0.2210, 0.2868, 0.1088, 0.0491, 0.1579, 0.0549, -0.3700, 0.2646,
  0.1506, 0.0211, 0.1600, 0.3239, 0.1369, 0.0138, 0.1196, 0.2183,
  -0.0438, 0.3149, 0.1840, 0.2861, -0.1830, 0.2837, -0.1932, 0.2471,
];

interface FIREPreset {
  label: string;
  description: string;
  annual_expenses: number;
  savings_rate: number;
}

export const FIRE_PRESETS: Record<FIREType, FIREPreset> = {
  lean: {
    label: "Lean FIRE",
    description: "Minimal expenses, frugal lifestyle",
    annual_expenses: 30_000,
    savings_rate: 0.60,
  },
  normal: {
    label: "Normal FIRE",
    description: "Moderate lifestyle, standard 4% rule",
    annual_expenses: 50_000,
    savings_rate: 0.40,
  },
  fat: {
    label: "Fat FIRE",
    description: "Comfortable expenses, premium lifestyle",
    annual_expenses: 100_000,
    savings_rate: 0.30,
  },
  coast: {
    label: "Coast FIRE",
    description: "Enough invested, no more contributions needed",
    annual_expenses: 50_000,
    savings_rate: 0.0,
  },
  barista: {
    label: "Barista FIRE",
    description: "Part-time income covers gap between expenses and withdrawals",
    annual_expenses: 40_000,
    savings_rate: 0.10,
  },
};

export const WITHDRAWAL_STRATEGIES: Record<
  WithdrawalStrategy,
  { label: string; description: string }
> = {
  constant_dollar: {
    label: "Constant Dollar (4% Rule)",
    description: "Fixed inflation-adjusted withdrawal (Bengen 1994)",
  },
  constant_percentage: {
    label: "Constant Percentage",
    description: "Fixed percentage of current portfolio value each year",
  },
  guyton_klinger: {
    label: "Guyton-Klinger Guardrails",
    description:
      "Dynamic rules with prosperity raises and capital preservation cuts (Guyton & Klinger 2006)",
  },
};

interface SimulationState {
  config: ScenarioConfig;
  setConfig: (config: Partial<ScenarioConfig>) => void;
  resetConfig: () => void;
  addLifeEvent: (event: LifeEvent) => void;
  removeLifeEvent: (index: number) => void;
  updateLifeEvent: (index: number, event: LifeEvent) => void;
  applyPreset: (type: FIREType) => void;
}

const DEFAULT_CONFIG: ScenarioConfig = {
  initial_portfolio: 1_000_000,
  annual_withdrawal: 40_000,
  return_distribution: HISTORICAL_RETURNS,
  n_trials: 10_000,
  n_years: 30,
  inflation_rate: 0.03,
  withdrawal_strategy: "constant_dollar",
  life_events: [],
};

export const useSimulationStore = create<SimulationState>((set) => ({
  config: DEFAULT_CONFIG,

  setConfig: (partial) =>
    set((state) => ({ config: { ...state.config, ...partial } })),

  resetConfig: () => set({ config: DEFAULT_CONFIG }),

  addLifeEvent: (event) =>
    set((state) => ({
      config: {
        ...state.config,
        life_events: [...(state.config.life_events ?? []), event],
      },
    })),

  removeLifeEvent: (index) =>
    set((state) => ({
      config: {
        ...state.config,
        life_events: (state.config.life_events ?? []).filter(
          (_, i) => i !== index
        ),
      },
    })),

  updateLifeEvent: (index, event) =>
    set((state) => ({
      config: {
        ...state.config,
        life_events: (state.config.life_events ?? []).map((e, i) =>
          i === index ? event : e
        ),
      },
    })),

  applyPreset: (type) =>
    set((state) => {
      const preset = FIRE_PRESETS[type];
      return {
        config: {
          ...state.config,
          annual_withdrawal: preset.annual_expenses,
        },
      };
    }),
}));
