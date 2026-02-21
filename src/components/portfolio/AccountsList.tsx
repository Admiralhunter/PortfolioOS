/**
 * Accounts list — create, select, and delete accounts.
 */

import { useState } from "react";
import { useAccounts, useDeleteAccount } from "../../hooks/useAccounts";
import { usePortfolioStore } from "../../stores/portfolio";
import { CreateAccountForm } from "./CreateAccountForm";

export function AccountsList() {
  const { data: accounts, isLoading, error } = useAccounts();
  const deleteAccount = useDeleteAccount();
  const { selectedAccountId, setSelectedAccountId } = usePortfolioStore();
  const [showForm, setShowForm] = useState(false);

  if (isLoading) {
    return <div className="p-4 text-muted-foreground">Loading accounts...</div>;
  }
  if (error) {
    return <div className="p-4 text-destructive">Error: {error.message}</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">Accounts</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-2 py-1 text-xs bg-primary text-primary-foreground rounded hover:bg-primary/90"
        >
          {showForm ? "Cancel" : "+ New"}
        </button>
      </div>

      {showForm && <CreateAccountForm onClose={() => setShowForm(false)} />}

      <div className="space-y-1">
        {accounts?.length === 0 && (
          <p className="text-sm text-muted-foreground py-2">
            No accounts yet. Create one to get started.
          </p>
        )}
        {accounts?.map((account) => (
          <div
            key={account.id}
            onClick={() => setSelectedAccountId(account.id)}
            className={`flex items-center justify-between p-2.5 rounded-md cursor-pointer transition-colors ${
              selectedAccountId === account.id
                ? "bg-primary/10 border border-primary/30"
                : "hover:bg-muted border border-transparent"
            }`}
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{account.name}</p>
              <p className="text-xs text-muted-foreground">{account.type}</p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (confirm(`Delete "${account.name}"?`)) {
                  deleteAccount.mutate(account.id);
                  if (selectedAccountId === account.id) {
                    setSelectedAccountId(null);
                  }
                }
              }}
              className="text-muted-foreground hover:text-destructive text-xs px-1"
              title="Delete account"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
