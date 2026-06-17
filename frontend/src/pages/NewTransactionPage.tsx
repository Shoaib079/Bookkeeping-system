import { FormEvent, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import {
  reactWriteEnabled,
  reactWriteExpensesEnabled,
  reactWriteSalesEnabled,
} from "../config/featureFlags";
import type { ApiError } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type {
  CreateExpenseResponse,
  CreateSaleResponse,
} from "../lib/api/types";
import { apiPost } from "../lib/api/writeClient";

type WriteTab = "sale" | "expense";

function todayIso(): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function parseAmount(raw: string): number | null {
  const parsed = Number(raw.replace(/,/g, ""));
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

export function NewTransactionPage() {
  const salesOn = reactWriteSalesEnabled();
  const expensesOn = reactWriteExpensesEnabled();
  const defaultTab: WriteTab = salesOn ? "sale" : "expense";

  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [tab, setTab] = useState<WriteTab>(defaultTab);
  const [date, setDate] = useState(todayIso());
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("TRY");
  const [notes, setNotes] = useState("");
  const [categoryName, setCategoryName] = useState("Office");
  const [subcategoryName, setSubcategoryName] = useState("Other");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saleResult, setSaleResult] = useState<CreateSaleResponse | null>(null);
  const [expenseResult, setExpenseResult] = useState<CreateExpenseResponse | null>(
    null,
  );

  if (!reactWriteEnabled()) {
    return (
      <section className="erp-placeholder">
        <h1>New Transaction</h1>
        <p>
          Write UI disabled. Set <code>VITE_ERP_REACT_WRITE_SALES=1</code> and/or{" "}
          <code>VITE_ERP_REACT_WRITE_EXPENSES=1</code>.
        </p>
      </section>
    );
  }

  async function handleSaleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedAmount = parseAmount(amount);
    if (parsedAmount === null) {
      setError("Enter a valid amount greater than zero.");
      return;
    }

    setLoading(true);
    setError(null);
    setSaleResult(null);
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
      setSaleResult(response);
      setAmount("");
      setNotes("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to save sale.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExpenseSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedAmount = parseAmount(amount);
    if (parsedAmount === null) {
      setError("Enter a valid amount greater than zero.");
      return;
    }
    const category = categoryName.trim();
    if (!category) {
      setError("Category name is required.");
      return;
    }

    setLoading(true);
    setError(null);
    setExpenseResult(null);
    try {
      const body: {
        date: string;
        amount: number;
        currency: string;
        payment_method: "Cash";
        notes: string;
        category_name: string;
        subcategory_name?: string;
      } = {
        date,
        amount: parsedAmount,
        currency,
        payment_method: "Cash",
        notes: notes.trim(),
        category_name: category,
      };
      const sub = subcategoryName.trim();
      if (sub) {
        body.subcategory_name = sub;
      }
      const response = await apiPost<CreateExpenseResponse>(
        "/api/v1/expenses",
        body,
        { session },
      );
      setExpenseResult(response);
      setAmount("");
      setNotes("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to save expense.");
    } finally {
      setLoading(false);
    }
  }

  function switchTab(next: WriteTab) {
    setTab(next);
    setError(null);
    setSaleResult(null);
    setExpenseResult(null);
  }

  return (
    <section className="erp-write-page">
      <header className="erp-page-header">
        <h1>New Transaction</h1>
        <p className="erp-page-header__meta">
          Write tabs call existing P2 APIs (requires matching{" "}
          <code>ERP_API_WRITE_*</code> server flags).
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      <nav className="erp-write-tabs" aria-label="Transaction type">
        {salesOn ? (
          <button
            type="button"
            className={tab === "sale" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"}
            onClick={() => switchTab("sale")}
          >
            Sale
          </button>
        ) : null}
        {expensesOn ? (
          <button
            type="button"
            className={
              tab === "expense" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"
            }
            onClick={() => switchTab("expense")}
          >
            Expense
          </button>
        ) : null}
      </nav>

      {tab === "sale" && salesOn ? (
        <form className="erp-write-form" onSubmit={handleSaleSubmit}>
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
          <p className="erp-muted">Payment method: Cash</p>
          <button type="submit" disabled={!session || loading}>
            {loading ? "Saving…" : "Save cash sale"}
          </button>
        </form>
      ) : null}

      {tab === "expense" && expensesOn ? (
        <form className="erp-write-form" onSubmit={handleExpenseSubmit}>
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
            Category
            <input
              type="text"
              value={categoryName}
              onChange={(event) => setCategoryName(event.target.value)}
              required
            />
          </label>
          <label>
            Subcategory
            <input
              type="text"
              value={subcategoryName}
              onChange={(event) => setSubcategoryName(event.target.value)}
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
          <p className="erp-muted">Payment method: Cash</p>
          <button type="submit" disabled={!session || loading}>
            {loading ? "Saving…" : "Save cash expense"}
          </button>
        </form>
      ) : null}

      {error ? <p className="erp-error">{error}</p> : null}
      {saleResult ? (
        <article className="erp-card erp-write-result">
          <h2>Sale saved</h2>
          <p>{saleResult.message}</p>
          <p className="erp-muted">
            Invoice {saleResult.invoice_number} · sale #{saleResult.sale_id}
          </p>
        </article>
      ) : null}
      {expenseResult ? (
        <article className="erp-card erp-write-result">
          <h2>Expense saved</h2>
          <p>{expenseResult.message}</p>
          <p className="erp-muted">Expense #{expenseResult.expense_id}</p>
        </article>
      ) : null}
    </section>
  );
}
