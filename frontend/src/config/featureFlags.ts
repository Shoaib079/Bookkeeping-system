export function reactPagesEnabled(): boolean {
  return import.meta.env.VITE_ERP_REACT_PAGES === "1";
}

export function reactWriteSalesEnabled(): boolean {
  return import.meta.env.VITE_ERP_REACT_WRITE_SALES === "1";
}
