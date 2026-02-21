/**
 * Simulation state store — current simulation configuration.
 */

import { create } from "zustand";
import type { SimulationConfig } from "../types";

interface SimulationState {
  config: SimulationConfig;
  setConfig: (config: Partial<SimulationConfig>) => void;
  resetConfig: () => void;
}

const DEFAULT_CONFIG: SimulationConfig = {
  initial_portfolio: 1_000_000,
  annual_withdrawal: 40_000,
  return_distribution: [],
  n_trials: 10_000,
  n_years: 30,
  inflation_rate: 0.03,
};

export const useSimulationStore = create<SimulationState>((set) => ({
  config: DEFAULT_CONFIG,
  setConfig: (partial) =>
    set((state) => ({ config: { ...state.config, ...partial } })),
  resetConfig: () => set({ config: DEFAULT_CONFIG }),
}));
