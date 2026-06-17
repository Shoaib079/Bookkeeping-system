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

export type CreateSaleRequest = {
  date: string;
  amount: number;
  currency: string;
  payment_method: "Cash" | "Card" | "Credit";
  notes?: string;
  customer_name?: string;
  card_bank_account_id?: number;
};

export type CreateSaleResponse = {
  sale_id: number;
  journal_entry_id: number | null;
  invoice_number: string;
  message: string;
  status: string;
};

export type CreateExpenseRequest = {
  date: string;
  amount: number;
  currency: string;
  payment_method: "Cash" | "Bank";
  notes?: string;
  category_name: string;
  subcategory_name?: string;
  bank_account_id?: number;
};

export type CreateExpenseResponse = {
  expense_id: number;
  journal_entry_id: number | null;
  message: string;
  status: string;
};

export type VoidTargetType =
  | "Sale"
  | "ExpenseRecord"
  | "Purchase"
  | "Payable"
  | "BankTransaction";

export type VoidRequest = {
  target_type: VoidTargetType;
  target_id: number;
  reason: string;
};

export type VoidResponse = {
  target_type: string;
  target_id: number;
  reversal_journal_entry_id: number | null;
  message: string;
  status: string;
};

export type CreatePurchaseRequest = {
  date: string;
  amount: number;
  currency: string;
  payment_method: "Cash" | "Bank" | "Credit";
  notes?: string;
  vendor_name: string;
  category_name: string;
  subcategory_name?: string;
  bank_account_id?: number;
};

export type CreatePurchaseResponse = {
  purchase_id: number;
  payable_id: number | null;
  journal_entry_id: number | null;
  message: string;
  status: string;
};

export type CreateReceivablePaymentRequest = {
  date: string;
  amount: number;
  currency: string;
  payment_method: "Cash" | "Bank";
  sale_id: number;
  notes?: string;
  customer_name?: string;
  bank_account_id?: number;
};

export type CreateReceivablePaymentResponse = {
  payment_id: number;
  journal_entry_id: number;
  sale_id: number;
  message: string;
  status: string;
};

export type CreateBankTransactionRequest = {
  date: string;
  amount: number;
  transaction_type: "deposit" | "withdrawal" | "transfer";
  bank_account_id: number;
  notes?: string;
  destination_bank_account_id?: number;
  currency?: string;
};

export type CreateBankTransactionResponse = {
  bank_transaction_id: number;
  paired_transaction_id: number | null;
  journal_entry_id: number | null;
  message: string;
  status: string;
};

export type PartnerMovementType =
  | "CapitalContribution"
  | "Drawing"
  | "Salary"
  | "Advance"
  | "Repayment"
  | "AdvanceOffset";

export type WorkerMovementType = "Salary" | "Advance" | "Repayment";

export type CreatePartnerMovementRequest = {
  partner_id: number;
  movement_type: PartnerMovementType;
  amount: number;
  date: string;
  bank_account_id?: number;
  notes?: string;
};

export type CreatePartnerMovementResponse = {
  movement_id: number;
  journal_entry_id: number;
  message: string;
  status: string;
};

export type CreateWorkerPaymentRequest = {
  worker_id: number;
  movement_type: WorkerMovementType;
  date: string;
  bank_account_id: number;
  amount?: number;
  gross_salary?: number;
  deductions?: number;
  advance_recovery?: number;
  pay_period?: string;
  notes?: string;
};

export type CreateWorkerPaymentResponse = {
  payment_id: number;
  journal_entry_id: number;
  message: string;
  status: string;
};
