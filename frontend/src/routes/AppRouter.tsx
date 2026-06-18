import type { ComponentType } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import {
  reactPagesEnabled,
  reactWriteEnabled,
} from "../config/featureFlags";
import { AppShell } from "../layouts/AppShell";
import { AuditLogPage } from "../pages/AuditLogPage";
import { InventoryPage } from "../pages/InventoryPage";
import { BudgetPage } from "../pages/BudgetPage";
import { BackupRestorePage } from "../pages/BackupRestorePage";
import { CompanySettingsPage } from "../pages/CompanySettingsPage";
import { PermissionsPage } from "../pages/PermissionsPage";
import { MembersPage } from "../pages/MembersPage";
import { routeSpecs, type RouteSpec } from "../lib/routes";
import { HomePage } from "../pages/HomePage";
import { BalanceSheetPage } from "../pages/BalanceSheetPage";
import { BankAccountsPage } from "../pages/BankAccountsPage";
import { BankingReadinessPage } from "../pages/BankingReadinessPage";
import { CashFlowPage } from "../pages/CashFlowPage";
import { ChartOfAccountsPage } from "../pages/ChartOfAccountsPage";
import { CustomersPage } from "../pages/CustomersPage";
import { ExpensesPage } from "../pages/ExpensesPage";
import { FiscalPeriodsPage } from "../pages/FiscalPeriodsPage";
import { JournalEntriesPage } from "../pages/JournalEntriesPage";
import { LedgerPage } from "../pages/LedgerPage";
import { OpeningBalancesPage } from "../pages/OpeningBalancesPage";
import { PartnerStatementPage } from "../pages/PartnerStatementPage";
import { PayablesPage } from "../pages/PayablesPage";
import { ProfitLossPage } from "../pages/ProfitLossPage";
import { PurchasesPage } from "../pages/PurchasesPage";
import { ReceivablesPage } from "../pages/ReceivablesPage";
import { ReconHealthPage } from "../pages/ReconHealthPage";
import { ReportsPage } from "../pages/ReportsPage";
import { SalesPage } from "../pages/SalesPage";
import { TransactionLedgerPage } from "../pages/TransactionLedgerPage";
import { TrialBalancePage } from "../pages/TrialBalancePage";
import { VendorsPage } from "../pages/VendorsPage";
import { WorkersPage } from "../pages/WorkersPage";
import { NewTransactionPage } from "../pages/NewTransactionPage";
import { PlaceholderPage } from "../pages/PlaceholderPage";

const READ_PAGES: Record<string, ComponentType> = {
  "/": HomePage,
  "/books/general-ledger": LedgerPage,
  "/books/trial-balance": TrialBalancePage,
  "/books/recon-health": ReconHealthPage,
  "/books/opening-balances": OpeningBalancesPage,
  "/books/budget": BudgetPage,
  "/books/chart-of-accounts": ChartOfAccountsPage,
  "/books/fiscal-periods": FiscalPeriodsPage,
  "/books/journal-entries": JournalEntriesPage,
  "/reports/balance-sheet": BalanceSheetPage,
  "/receivables": ReceivablesPage,
  "/payables": PayablesPage,
  "/partners": PartnerStatementPage,
  "/banking": BankingReadinessPage,
  "/banking/accounts": BankAccountsPage,
  "/reports": ReportsPage,
  "/reports/profit-loss": ProfitLossPage,
  "/reports/cash-flow": CashFlowPage,
  "/transactions/ledger": TransactionLedgerPage,
  "/vendors": VendorsPage,
  "/sales": SalesPage,
  "/expenses": ExpensesPage,
  "/workers": WorkersPage,
  "/customers": CustomersPage,
  "/inventory": InventoryPage,
  "/purchases": PurchasesPage,
  "/settings/audit-log": AuditLogPage,
  "/settings/company": CompanySettingsPage,
  "/settings/backup-restore": BackupRestorePage,
  "/settings/members": MembersPage,
  "/settings/permissions": PermissionsPage,
};

const WRITE_PAGES: Record<string, ComponentType> = {
  "/transactions/new": NewTransactionPage,
};

function RoutePage({ route }: { route: RouteSpec }) {
  if (!reactPagesEnabled()) {
    return <PlaceholderPage />;
  }
  if (route.path in WRITE_PAGES && reactWriteEnabled()) {
    const Page = WRITE_PAGES[route.path];
    return <Page />;
  }
  if (route.path in READ_PAGES) {
    const Page = READ_PAGES[route.path];
    return <Page />;
  }
  return <PlaceholderPage />;
}

export function AppRouter() {
  const routes = routeSpecs();

  return (
    <Routes>
      <Route element={<AppShell />}>
        {routes.map((route) =>
          route.path === "/" ? (
            <Route key={route.path} index element={<RoutePage route={route} />} />
          ) : (
            <Route
              key={route.path}
              path={route.path.replace(/^\//, "")}
              element={<RoutePage route={route} />}
            />
          ),
        )}
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
