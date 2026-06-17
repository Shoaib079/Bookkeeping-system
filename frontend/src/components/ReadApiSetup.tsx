import { useState } from "react";

import {
  clearReadSession,
  getReadSession,
  setReadSession,
} from "../lib/api/session";

export function ReadApiSetup({ onSaved }: { onSaved?: () => void }) {
  const existing = getReadSession();
  const [token, setToken] = useState(existing?.accessToken ?? "");
  const [companyId, setCompanyId] = useState(
    existing ? String(existing.companyId) : "",
  );
  const [saved, setSaved] = useState(false);

  function handleSave(event: React.FormEvent) {
    event.preventDefault();
    const parsedCompanyId = Number(companyId);
    if (!token.trim() || !Number.isFinite(parsedCompanyId)) {
      return;
    }
    setReadSession({
      accessToken: token.trim(),
      companyId: parsedCompanyId,
    });
    setSaved(true);
    onSaved?.();
    window.setTimeout(() => setSaved(false), 2000);
  }

  function handleClear() {
    clearReadSession();
    setToken("");
    setCompanyId("");
    onSaved?.();
  }

  return (
    <section className="erp-read-api-setup">
      <h2>Read API session</h2>
      <p>
        Provide a bearer token and company id to load P1 read endpoints. This is
        a dev helper — production login UI is deferred.
      </p>
      <form className="erp-read-api-setup__form" onSubmit={handleSave}>
        <label>
          Bearer token
          <input
            type="password"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            autoComplete="off"
          />
        </label>
        <label>
          Company id
          <input
            type="number"
            min={1}
            value={companyId}
            onChange={(event) => setCompanyId(event.target.value)}
          />
        </label>
        <div className="erp-read-api-setup__actions">
          <button type="submit">Save session</button>
          <button type="button" onClick={handleClear}>
            Clear
          </button>
        </div>
      </form>
      {saved ? <p className="erp-read-api-setup__saved">Session saved.</p> : null}
    </section>
  );
}
