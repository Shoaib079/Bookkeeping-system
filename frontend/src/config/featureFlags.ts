export function reactPagesEnabled(): boolean {
  return import.meta.env.VITE_ERP_REACT_PAGES === "1";
}

export function reactWriteSalesEnabled(): boolean {
  return import.meta.env.VITE_ERP_REACT_WRITE_SALES === "1";
}

export function reactWriteExpensesEnabled(): boolean {
  return import.meta.env.VITE_ERP_REACT_WRITE_EXPENSES === "1";
}

export function reactWriteVoidsEnabled(): boolean {
  return import.meta.env.VITE_ERP_REACT_WRITE_VOIDS === "1";
}

export function reactWritePurchasesEnabled(): boolean {
  return import.meta.env.VITE_ERP_REACT_WRITE_PURCHASES === "1";
}

export function reactWriteReceivablePaymentsEnabled(): boolean {
  return import.meta.env.VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS === "1";
}

export function reactWriteEnabled(): boolean {
  return (
    reactWriteSalesEnabled() ||
    reactWriteExpensesEnabled() ||
    reactWriteVoidsEnabled() ||
    reactWritePurchasesEnabled() ||
    reactWriteReceivablePaymentsEnabled()
  );
}
