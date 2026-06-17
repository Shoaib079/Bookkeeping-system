import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ReadApiSetup } from "../components/ReadApiSetup";
import { apiGet } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type { PartnerStatementResponse } from "../lib/api/types";

function todayIso(): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function yearStartIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-01-01`;
}

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function PartnerStatementPage() {
  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [partnerId, setPartnerId] = useState(
    searchParams.get("partner_id") ?? "",
  );
  const [fromDate, setFromDate] = useState(
    searchParams.get("from_date") ?? yearStartIso(),
  );
  const [toDate, setToDate] = useState(
    searchParams.get("to_date") ?? todayIso(),
  );
  const [statement, setStatement] = useState<PartnerStatementResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session) {
      return;
    }
    const parsedPartnerId = Number(partnerId);
    if (!Number.isFinite(parsedPartnerId) || parsedPartnerId < 1) {
      setStatement(null);
      return;
    }
    if (!fromDate || !toDate) {
      setStatement(null);
      return;
    }

    const params = new URLSearchParams({
      from_date: fromDate,
      to_date: toDate,
    });

    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
// P1 read: /api/v1/partners/{partner_id}/statement
        const data = await apiGet<PartnerStatementResponse>(
          `/api/v1/partners/${parsedPartnerId}/statement?${params.toString()}`,
          { session, companyScoped: true },
        );
        if (!cancelled) {
          setStatement(data);
        }
      } catch (err) {
        if (!cancelled) {
          const detail =
            err && typeof err === "object" && "detail" in err
              ? String((err as { detail: string }).detail)
              : "Failed to load partner statement.";
          setError(detail);
          setStatement(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [session, partnerId, fromDate, toDate]);

  function handleFilterSubmit(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (partnerId) {
      next.set("partner_id", partnerId);
    }
    if (fromDate) {
      next.set("from_date", fromDate);
    }
    if (toDate) {
      next.set("to_date", toDate);
    }
    setSearchParams(next);
  }

  return (
    <section className="erp-partner-statement-page">
      <header className="erp-page-header">
        <h1>Partner Statement</h1>
        <p className="erp-page-header__meta">
          Read-only settlement via `/api/v1/partners/{"{partner_id}"}/statement`
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      <form className="erp-ledger-filters" onSubmit={handleFilterSubmit}>
        <label>
          Partner id
          <input
            type="number"
            min={1}
            value={partnerId}
            onChange={(event) => setPartnerId(event.target.value)}
            required
          />
        </label>
        <label>
          From date
          <input
            type="date"
            value={fromDate}
            onChange={(event) => setFromDate(event.target.value)}
            required
          />
        </label>
        <label>
          To date
          <input
            type="date"
            value={toDate}
            onChange={(event) => setToDate(event.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={!session}>
          Apply filters
        </button>
      </form>

      {session && loading ? <p>Loading…</p> : null}
      {session && error ? <p className="erp-error">{error}</p> : null}

      {statement ? (
        <>
          <div className="erp-ledger-summary">
            <span>Partner: {statement.partner_name}</span>
            <span>Opening: {formatMoney(statement.opening_position)}</span>
            <span>Closing: {formatMoney(statement.closing_position)}</span>
            <span>Status: {statement.status}</span>
            <span>
              Reconciled: {statement.reconciliation_ok ? "Yes" : "No"}
            </span>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Section</th>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Reference</th>
                  <th>Inflow</th>
                  <th>Outflow</th>
                  <th>Position</th>
                </tr>
              </thead>
              <tbody>
                {statement.detail_lines.map((line, index) => (
                  <tr key={`${line.source_id ?? "line"}-${index}`}>
                    <td>{line.line_date ?? ""}</td>
                    <td>{line.section_key}</td>
                    <td>{line.type_key}</td>
                    <td>{line.description}</td>
                    <td>{line.reference}</td>
                    <td>{line.inflow ? formatMoney(line.inflow) : ""}</td>
                    <td>{line.outflow ? formatMoney(line.outflow) : ""}</td>
                    <td>{formatMoney(line.running_position)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {session && !partnerId ? (
        <p className="erp-muted">Enter a partner id to load the statement.</p>
      ) : null}
    </section>
  );
}
