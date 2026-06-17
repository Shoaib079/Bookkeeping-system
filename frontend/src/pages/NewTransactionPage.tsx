import { FormEvent, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { reactWriteSalesEnabled } from "../config/featureFlags";
import type { ApiError } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { CreateSaleResponse } from "../lib/api/types";
import { apiPost } from "../lib/api/writeClient";

function todayIso(): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function NewTransactionPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [date, setDate] = useState(todayIso());
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("TRY");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CreateSaleResponse | null>(null);

  if (!reactWriteSalesEnabled()) {
    return (
      <section className="erp-placeholder">
        <h1>New Transaction</h1>
        <p>
          Write UI disabled. Set <code>VITE_ERP_REACT_WRITE_SALES=1</code> to
          enable the cash sale form.
        </p>
      </section>
    );
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedAmount = Number(amount.replace(/,/g, ""));
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setError("Enter a valid amount greater than zero.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await apiPost<CreateSaleResponse>(
        "/api/v1/sales",
        {
          date,
          amount: parsedAmount,
          currency,
          payment_method: "Cash",
          notes: notes.trim(),
        },
        { session },
      );
      setResult(response);
      setAmount("");
      setNotes("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to save sale.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="erp-write-page">
      <header className="erp-page-header">
        <h1>New Transaction</h1>
        <p className="erp-page-header__meta">
          Cash sale via <code>POST /api/v1/sales</code> (requires{" "}
          <code>ERP_API_WRITE_SALES=1</code>)
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      <form className="erp-write-form" onSubmit={handleSubmit}>
        <label>
          Date
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            required
          />
        </label>
        <label>
          Amount
          <input
            type="text"
            inputMode="decimal"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="0.00"
            required
          />
        </label>
        <label>
          Currency
          <input
            type="text"
            value={currency}
            onChange={(event) => setCurrency(event.target.value.toUpperCase())}
            maxLength={3}
            required
          />
        </label>
        <label>
          Notes
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
          />
        </label>
        <p className="erp-muted">Payment method: Cash (fixed in FR-08)</p>
        <button type="submit" disabled={!session || loading}>
          {loading ? "Saving…" : "Save cash sale"}
        </button>
      </form>

      {error ? <p className="erp-error">{error}</p> : null}
      {result ? (
        <article className="erp-card erp-write-result">
          <h2>Sale saved</h2>
          <p>{result.message}</p>
          <p className="erp-muted">
            Invoice {result.invoice_number} · sale #{result.sale_id}
          </p>
        </article>
      ) : null}
    </section>
  );
}
