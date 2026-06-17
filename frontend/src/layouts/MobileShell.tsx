import { NavLink, Outlet } from "react-router-dom";

const BOTTOM_LINKS = [
  { label: "Home", to: "/" },
  { label: "Money", to: "/banking" },
  { label: "Reports", to: "/reports" },
  { label: "More", to: "/settings/company" },
];

export function MobileShell() {
  return (
    <div className="erp-mobile-shell">
      <header className="erp-mobile-header">
        <strong>ERP</strong>
      </header>
      <main className="erp-mobile-main">
        <Outlet />
      </main>
      <nav className="erp-mobile-bottom-nav">
        {BOTTOM_LINKS.map((link) => (
          <NavLink key={link.to} to={link.to} className="erp-mobile-nav-link">
            {link.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
