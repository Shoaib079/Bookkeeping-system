const TOKEN_KEY = "erp_access_token";
const COMPANY_KEY = "erp_company_id";

export type ReadSession = {
  accessToken: string;
  companyId: number;
};

function devSessionFromEnv(): ReadSession | null {
  const token = import.meta.env.VITE_DEV_BEARER_TOKEN;
  const companyRaw = import.meta.env.VITE_DEV_COMPANY_ID;
  if (!token || !companyRaw) {
    return null;
  }
  const companyId = Number(companyRaw);
  if (!Number.isFinite(companyId)) {
    return null;
  }
  return { accessToken: token, companyId };
}

export function getReadSession(): ReadSession | null {
  const fromEnv = devSessionFromEnv();
  if (fromEnv) {
    return fromEnv;
  }
  const accessToken = sessionStorage.getItem(TOKEN_KEY);
  const companyRaw = sessionStorage.getItem(COMPANY_KEY);
  if (!accessToken || !companyRaw) {
    return null;
  }
  const companyId = Number(companyRaw);
  if (!Number.isFinite(companyId)) {
    return null;
  }
  return { accessToken, companyId };
}

export function setReadSession(session: ReadSession): void {
  sessionStorage.setItem(TOKEN_KEY, session.accessToken);
  sessionStorage.setItem(COMPANY_KEY, String(session.companyId));
}

export function clearReadSession(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(COMPANY_KEY);
}

export function hasReadSession(): boolean {
  return getReadSession() !== null;
}
