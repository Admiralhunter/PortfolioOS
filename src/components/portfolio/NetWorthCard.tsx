/**
 * Net worth summary card — displays total portfolio value and gain/loss.
 */

import { useHoldings } from "../../hooks/useHoldings";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

export function NetWorthCard() {
  const { data: holdings } = useHoldings();

  const totalCostBasis = holdings?.reduce((sum, h) => sum + h.cost_basis, 0) ?? 0;
  const holdingsCount = holdings?.length ?? 0;

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="p-4 bg-card border border-border rounded-lg">
        <p className="text-xs text-muted-foreground mb-1">Total Cost Basis</p>
        <p className="text-2xl font-bold text-foreground">{formatCurrency(totalCostBasis)}</p>
      </div>
      <div className="p-4 bg-card border border-border rounded-lg">
        <p className="text-xs text-muted-foreground mb-1">Holdings</p>
        <p className="text-2xl font-bold text-foreground">{holdingsCount}</p>
      </div>
    </div>
  );
}
