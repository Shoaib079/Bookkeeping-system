import { useLocation } from "react-router-dom";

export function PlaceholderPage() {
  const location = useLocation();
  return (
    <section className="erp-placeholder">
      <h1>Route shell</h1>
      <p>
        <strong>Path:</strong> {location.pathname}
      </p>
      <p>Page implementation deferred to FASTAPI-REACT-06.</p>
    </section>
  );
}
