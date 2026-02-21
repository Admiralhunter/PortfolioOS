/**
 * TanStack Query hooks for app preferences via IPC.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export function usePreferences() {
  return useQuery({
    queryKey: ["preferences"],
    queryFn: async () => {
      const response = await window.api.system.getPreferences();
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
  });
}

export function useSetPreference() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      const response = await window.api.system.setPreference(key, value);
      if (!response.success) throw new Error(response.error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["preferences"] });
    },
  });
}
