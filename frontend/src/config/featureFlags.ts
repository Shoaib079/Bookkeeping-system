export function reactPagesEnabled(): boolean {
  return import.meta.env.VITE_ERP_REACT_PAGES === "1";
}
