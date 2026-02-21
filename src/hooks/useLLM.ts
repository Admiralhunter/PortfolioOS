/**
 * TanStack Query hooks for LLM provider operations via IPC.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AddProviderParams, LLMOptions } from "../types";

export function useProviders() {
  return useQuery({
    queryKey: ["llm-providers"],
    queryFn: async () => {
      const response = await window.api.llm.listProviders();
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
  });
}

export function useAddProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: AddProviderParams) => {
      const response = await window.api.llm.addProvider(params);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-providers"] });
    },
  });
}

export function useDeleteProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (providerId: string) => {
      const response = await window.api.llm.deleteProvider(providerId);
      if (!response.success) throw new Error(response.error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-providers"] });
    },
  });
}

export function useSetDefaultProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (providerId: string) => {
      const response = await window.api.llm.setDefault(providerId);
      if (!response.success) throw new Error(response.error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["llm-providers"] });
    },
  });
}

export function useLLMSend() {
  return useMutation({
    mutationFn: async ({
      prompt,
      options,
    }: {
      prompt: string;
      options?: LLMOptions;
    }) => {
      const response = await window.api.llm.send(prompt, options);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
  });
}
