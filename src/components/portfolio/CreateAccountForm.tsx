/**
 * Create account form — inline form for adding new accounts.
 */

import { useState } from "react";
import { useCreateAccount } from "../../hooks/useAccounts";
import type { CreateAccountParams } from "../../types";

const ACCOUNT_TYPES = [
  "401k",
  "Traditional IRA",
  "Roth IRA",
  "HSA",
  "529",
  "Taxable Brokerage",
  "Other",
];

interface CreateAccountFormProps {
  onClose: () => void;
}

export function CreateAccountForm({ onClose }: CreateAccountFormProps) {
  const createAccount = useCreateAccount();
  const [formData, setFormData] = useState<CreateAccountParams>({
    name: "",
    type: "Taxable Brokerage",
    institution: "",
  });

  const handleCreate = () => {
    if (!formData.name.trim()) return;
    createAccount.mutate(formData, {
      onSuccess: () => {
        onClose();
      },
    });
  };

  return (
    <div className="p-3 bg-muted rounded-md space-y-2">
      <input
        type="text"
        placeholder="Account name"
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        className="w-full px-2 py-1.5 text-sm bg-input border border-border rounded text-foreground placeholder:text-muted-foreground"
      />
      <select
        value={formData.type}
        onChange={(e) => setFormData({ ...formData, type: e.target.value })}
        className="w-full px-2 py-1.5 text-sm bg-input border border-border rounded text-foreground"
      >
        {ACCOUNT_TYPES.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
      <input
        type="text"
        placeholder="Institution (optional)"
        value={formData.institution ?? ""}
        onChange={(e) => setFormData({ ...formData, institution: e.target.value })}
        className="w-full px-2 py-1.5 text-sm bg-input border border-border rounded text-foreground placeholder:text-muted-foreground"
      />
      <button
        onClick={handleCreate}
        disabled={createAccount.isPending}
        className="w-full px-2 py-1.5 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
      >
        {createAccount.isPending ? "Creating..." : "Create Account"}
      </button>
    </div>
  );
}
