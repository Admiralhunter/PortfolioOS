/**
 * Market dashboard — placeholder for price charts and macro data.
 */

export function MarketDashboard() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-foreground">Market Intelligence</h2>
      <div className="bg-card border border-border rounded-lg p-8 text-center">
        <p className="text-muted-foreground">
          Market data, price charts, and macro indicators coming soon.
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          Powered by Yahoo Finance and FRED data feeds.
        </p>
      </div>
    </div>
  );
}
