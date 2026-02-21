/**
 * TanStack Query hooks for account CRUD operations via IPC.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { CreateAccountParams } from "../types";

export function useAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const response = await window.api.portfolio.listAccounts();
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
  });
}

export function useCreateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: CreateAccountParams) => {
      const response = await window.api.portfolio.createAccount(params);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}

export function useUpdateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, params }: { id: string; params: Partial<CreateAccountParams> }) => {
      const response = await window.api.portfolio.updateAccount(id, params);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}

export function useDeleteAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const response = await window.api.portfolio.deleteAccount(id);
      if (!response.success) throw new Error(response.error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
}
