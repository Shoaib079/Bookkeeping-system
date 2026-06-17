export type MeResponse = {
  id: number;
  username: string;
  display_name?: string | null;
  is_active: boolean;
};

export type CompanyAccessItem = {
  company_id: number;
  company_name: string;
  role: string;
  is_default?: boolean;
};

export type CompaniesResponse = {
  companies: CompanyAccessItem[];
};

export type ProfitLossResponse = {
  start_date: string;
  end_date: string;
  total_income: number;
  total_expenses: number;
  net: number;
  margin_pct: number | null;
  is_profit: boolean;
};

export type LedgerRow = {
  date: string;
  reference: string;
  description: string;
  debit: number;
  credit: number;
  running_balance: number;
  account_code: string;
  account_name: string;
};

export type LedgerPageResponse = {
  rows: LedgerRow[];
  filters: {
    account_id: number;
    start_date: string | null;
    end_date: string | null;
    search_keyword: string | null;
  };
  opening_balance: number;
  closing_balance: number;
  row_count: number;
  total_debit: number;
  total_credit: number;
  account_type: string;
  current_balance: number;
};
