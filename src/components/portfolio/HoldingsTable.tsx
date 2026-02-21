/**
 * Holdings table — displays holdings for the selected account.
 */

import { useHoldings } from "../../hooks/useHoldings";
import { usePortfolioStore } from "../../stores/portfolio";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

function formatNumber(value: number, decimals = 4): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function HoldingsTable() {
  const { selectedAccountId } = usePortfolioStore();
  const { data: holdings, isLoading, error } = useHoldings(selectedAccountId ?? undefined);

  if (!selectedAccountId) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        Select an account to view holdings
      </div>
    );
  }

  if (isLoading) {
    return <div className="p-4 text-muted-foreground text-sm">Loading holdings...</div>;
  }

  if (error) {
    return <div className="p-4 text-destructive text-sm">Error: {error.message}</div>;
  }

  if (!holdings || holdings.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No holdings found. Import transactions to see holdings.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-muted-foreground">
            <th className="text-left py-2 px-3 font-medium">Symbol</th>
            <th className="text-left py-2 px-3 font-medium">Type</th>
            <th className="text-right py-2 px-3 font-medium">Shares</th>
            <th className="text-right py-2 px-3 font-medium">Cost Basis</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) => (
            <tr key={holding.id} className="border-b border-border/50 hover:bg-muted/50">
              <td className="py-2 px-3 font-medium text-foreground">{holding.symbol}</td>
              <td className="py-2 px-3 text-muted-foreground">{holding.asset_type}</td>
              <td className="py-2 px-3 text-right text-foreground">{formatNumber(holding.shares)}</td>
              <td className="py-2 px-3 text-right text-foreground">{formatCurrency(holding.cost_basis)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
