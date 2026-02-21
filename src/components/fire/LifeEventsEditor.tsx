/**
 * Life events editor — add, edit, and remove temporal events
 * that affect the simulation (windfalls, expenses, income changes).
 */

import { useState } from "react";
import { useSimulationStore } from "../../stores/simulation";
import type { LifeEvent, LifeEventType } from "../../types";

const EVENT_TYPES: Record<LifeEventType, { label: string }> = {
  windfall: { label: "Windfall" },
  expense: { label: "One-time Expense" },
  income_change: { label: "Income Change" },
  savings_rate_change: { label: "Savings Rate Change" },
};

const INPUT_CLASS =
  "w-full px-3 py-2 bg-muted border border-border rounded-md text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary";

function formatCurrency(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `$${(abs / 1_000).toFixed(0)}K`;
  return `$${abs.toFixed(0)}`;
}

function EventRow({ event, onRemove }: { event: LifeEvent; onRemove: () => void }) {
  const isPositive = event.type === "windfall" || event.type === "income_change";
  return (
    <div className="flex items-center justify-between p-3 rounded-md bg-muted border border-border">
      <div className="flex items-center gap-3">
        <span className={`text-xs font-mono px-2 py-0.5 rounded ${isPositive ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}`}>
          Yr {event.year}
        </span>
        <div>
          <p className="text-sm text-foreground">{EVENT_TYPES[event.type].label}</p>
          <p className="text-xs text-muted-foreground">{event.amount >= 0 ? "+" : ""}{formatCurrency(event.amount)}</p>
        </div>
      </div>
      <button onClick={onRemove} className="text-muted-foreground hover:text-destructive text-xs transition-colors">
        Remove
      </button>
    </div>
  );
}

function AddEventForm({ maxYear, onAdd, onCancel }: { maxYear: number; onAdd: (e: LifeEvent) => void; onCancel: () => void }) {
  const [event, setEvent] = useState<LifeEvent>({ year: 5, type: "windfall", amount: 50_000 });

  return (
    <div className="p-3 rounded-md border border-primary/30 bg-primary/5 space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Year</label>
          <input type="number" value={event.year} onChange={(e) => setEvent({ ...event, year: Number(e.target.value) })} min={0} max={maxYear} className={INPUT_CLASS} />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Type</label>
          <select value={event.type} onChange={(e) => setEvent({ ...event, type: e.target.value as LifeEventType })} className={INPUT_CLASS}>
            {(Object.keys(EVENT_TYPES) as LifeEventType[]).map((t) => (
              <option key={t} value={t}>{EVENT_TYPES[t].label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Amount ($)</label>
          <input type="number" value={event.amount} onChange={(e) => setEvent({ ...event, amount: Number(e.target.value) })} className={INPUT_CLASS} />
        </div>
      </div>
      <div className="flex gap-2">
        <button onClick={() => { onAdd(event); onCancel(); }} className="flex-1 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors">
          Add Life Event
        </button>
      </div>
    </div>
  );
}

export function LifeEventsEditor() {
  const { config, addLifeEvent, removeLifeEvent } = useSimulationStore();
  const events = config.life_events ?? [];
  const [isAdding, setIsAdding] = useState(false);

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Life Events</h3>
        <button onClick={() => setIsAdding(!isAdding)} className="text-xs text-primary hover:text-primary/80 transition-colors">
          {isAdding ? "Cancel" : "+ Add Event"}
        </button>
      </div>
      {events.length === 0 && !isAdding && (
        <p className="text-xs text-muted-foreground text-center py-4">
          No life events configured. Add windfalls, expenses, or income changes.
        </p>
      )}
      {events.length > 0 && (
        <div className="space-y-2">
          {events.map((event, i) => (
            <EventRow key={i} event={event} onRemove={() => removeLifeEvent(i)} />
          ))}
        </div>
      )}
      {isAdding && <AddEventForm maxYear={config.n_years ?? 50} onAdd={addLifeEvent} onCancel={() => setIsAdding(false)} />}
    </div>
  );
}
