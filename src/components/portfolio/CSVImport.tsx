/**
 * CSV import flow — file picker, progress, and results.
 *
 * Uses Electron's dialog API to open a file picker, then routes
 * the import through the Python sidecar via IPC.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { usePortfolioStore } from "../../stores/portfolio";
import type { ImportResult } from "../../types";

export function CSVImport() {
  const { selectedAccountId } = usePortfolioStore();
  const queryClient = useQueryClient();
  const [result, setResult] = useState<ImportResult | null>(null);

  const importMutation = useMutation({
    mutationFn: async (filePath: string) => {
      if (!selectedAccountId) throw new Error("No account selected");
      const response = await window.api.portfolio.importCSV(filePath, selectedAccountId);
      if (!response.success) throw new Error(response.error);
      return response.data!;
    },
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["holdings"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });

  const handleFileSelect = () => {
    // In Electron, we'd use dialog.showOpenDialog. For now, use a
    // file input as a fallback that works in the renderer context.
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        // Electron File objects have a `path` property
        const filePath = (file as File & { path?: string }).path ?? file.name;
        importMutation.mutate(filePath);
      }
    };
    input.click();
  };

  if (!selectedAccountId) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Select an account before importing transactions.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Import CSV</h3>
        <button
          onClick={handleFileSelect}
          disabled={importMutation.isPending}
          className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
        >
          {importMutation.isPending ? "Importing..." : "Choose File"}
        </button>
      </div>

      {importMutation.isError && (
        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded text-sm text-destructive">
          {importMutation.error.message}
        </div>
      )}

      {result && (
        <div className="p-3 bg-success/10 border border-success/30 rounded text-sm space-y-1">
          <p className="text-success font-medium">Import complete</p>
          <p className="text-foreground">
            {result.transactions_imported} transactions imported,{" "}
            {result.holdings_reconciled} holdings reconciled.
          </p>
          {result.errors.length > 0 && (
            <div className="mt-2">
              <p className="text-warning text-xs font-medium">
                {result.errors.length} warning(s):
              </p>
              <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                {result.errors.slice(0, 5).map((err, i) => (
                  <li key={i}>- {err}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Supports CSV files with columns for date, symbol, type, quantity, price, and fees.
        Column mapping is flexible.
      </p>
    </div>
  );
}
