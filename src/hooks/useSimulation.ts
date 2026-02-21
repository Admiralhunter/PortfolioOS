/**
 * TanStack Query hook for running simulations via IPC.
 */

import { useMutation } from "@tanstack/react-query";
import type { SimulationConfig, ScenarioConfig } from "../types";

export function useRunSimulation() {
  return useMutation({
    mutationFn: async (config: SimulationConfig) => {
      const response = await window.api.simulation.run(config);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
  });
}

export function useRunScenario() {
  return useMutation({
    mutationFn: async (config: ScenarioConfig) => {
      const response = await window.api.simulation.runScenario(config);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
  });
}

export function useRunSensitivity() {
  return useMutation({
    mutationFn: async (config: ScenarioConfig & { vary_param: string; values: number[] }) => {
      const response = await window.api.simulation.sensitivity(config);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
  });
}
