import { NavLink, Outlet } from "react-router-dom";

const PRIMARY_LINKS = [
  { label: "Home", to: "/" },
  { label: "Ledger", to: "/books/general-ledger" },
  { label: "Banking", to: "/banking" },
  { label: "Reports", to: "/reports" },
];

export function DesktopShell() {
  return (
    <div className="erp-desktop-shell">
      <header className="erp-desktop-header">
        <strong>ERP</strong>
        <span className="erp-desktop-header__meta">Desktop shell</span>
      </header>
      <div className="erp-desktop-body">
        <aside className="erp-desktop-sidebar">
          <nav>
            {PRIMARY_LINKS.map((link) => (
              <NavLink key={link.to} to={link.to} className="erp-nav-link">
                {link.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="erp-desktop-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
