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

export type CashFlowRow = {
  date: string;
  description: string;
  type: string;
  inflow: number;
  outflow: number;
};

export type CashFlowResponse = {
  start_date: string;
  end_date: string;
  operating_rows: CashFlowRow[];
  financing_rows: CashFlowRow[];
  op_in: number;
  op_out: number;
  fin_in: number;
  fin_out: number;
  net_op: number;
  net_fin: number;
  net_total: number;
  has_cash_accounts: boolean;
};

export type TransactionHistoryRow = {
  date: string;
  type: string;
  reference: string;
  party: string;
  category: string;
  subcategory: string;
  amount: number;
  currency: string;
  method: string;
  description: string;
  status: string;
  created_by: string;
  source_type: string;
  source_id: number;
  company_id: number;
};

export type TransactionHistoryResponse = {
  rows: TransactionHistoryRow[];
  filters: {
    start_date: string;
    end_date: string;
    search_keyword: string | null;
    type_filter: string;
    show_voided: boolean;
  };
  row_count: number;
};

export type CoaRow = {
  id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  currency: string | null;
  is_active: boolean;
  company_id: number;
};

export type CoaListResponse = {
  rows: CoaRow[];
  row_count: number;
};

export type PartnerListRow = {
  id: number;
  name: string;
  profit_share_pct: number;
  is_active: boolean;
  company_id: number;
};

export type PartnersListResponse = {
  rows: PartnerListRow[];
  row_count: number;
};

export type BankAccountListRow = {
  id: number;
  name: string;
  bank_name: string | null;
  kind: string;
  currency: string | null;
  is_active: boolean;
  company_id: number;
};

export type BankAccountsListResponse = {
  rows: BankAccountListRow[];
  row_count: number;
};

export type WorkerListRow = {
  id: number;
  name: string;
  role: string | null;
  is_active: boolean;
  company_id: number;
};

export type WorkersListResponse = {
  rows: WorkerListRow[];
  row_count: number;
};

export type BalanceSheetResponse = {
  as_of: string;
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
  net_income: number;
  base_equity: number;
  balanced: boolean;
  imbalance: number;
};

export type ReceivableRow = {
  id: number;
  invoice_number: string;
  customer_name: string;
  date: string;
  due_date: string | null;
  amount: number;
  paid_amount: number;
  balance: number;
  status: string;
};

export type ReceivablesPageResponse = {
  rows: ReceivableRow[];
  outstanding: number;
  overdue: number;
  open_count: number;
  showing_count: number;
};

export type PayableRow = {
  id: number;
  date: string;
  vendor_name: string;
  due_date: string;
  invoice_amount: number;
  paid_amount: number;
  balance: number;
  status: string;
};

export type PayablesPageResponse = {
  rows: PayableRow[];
  total_outstanding: number;
  overdue: number;
  showing_count: number;
};

export type PartnerStatementDetailLine = {
  line_date: string | null;
  section_key: string;
  type_key: string;
  description: string;
  reference: string;
  gross_amount: number;
  inflow: number;
  outflow: number;
  signed_amount: number;
  net_effect: number;
  running_position: number;
  source_id: number | null;
};

export type PartnerStatementWarning = {
  key: string;
  kwargs: Record<string, unknown>;
};

export type PartnerStatementResponse = {
  partner_id: number;
  partner_name: string;
  partner_is_active: boolean;
  from_date: string;
  to_date: string;
  opening_position: number;
  opening_capital: number;
  opening_current: number;
  opening_advances: number;
  capital_contributions: number;
  profit_allocated: number;
  repayments: number;
  drawings: number;
  salary: number;
  advances_taken: number;
  loss_allocated: number;
  advance_offsets: number;
  closing_position: number;
  closing_capital: number;
  closing_current: number;
  closing_advances: number;
  net_position_change: number;
  status: string;
  status_amount: number;
  warnings: PartnerStatementWarning[];
  reconciliation_ok: boolean;
  detail_lines: PartnerStatementDetailLine[];
  company_id: number;
};

export type ReadinessBlocker = {
  kind: string;
  count: number;
};

export type StatementReadinessItem = {
  import_id: number;
  file_name: string;
  period: string;
  complete: boolean;
  complete_tri: string;
  reconciled: boolean;
  reconciled_tri: string;
  tie_out: string;
  tie_out_available: boolean;
  declared_movement: number | null;
  row_signed_total: number | null;
  tie_out_delta: number | null;
  remaining_rows: number;
  review_pending: number;
  failed_blocked: number;
  row_counts_by_status: Record<string, number>;
  drill_section: string;
  company_id: number;
  blockers: ReadinessBlocker[];
};

export type BankingReadinessResponse = {
  items: StatementReadinessItem[];
  meta?: {
    limit: number;
    count: number;
  };
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

export type ReconciliationMatchType =
  | "generic_deposit"
  | "bank_charge"
  | "deposit_clearing"
  | "vendor_outflow"
  | "partner"
  | "worker"
  | "equity"
  | "cc_bill_payment";

export type ReconciliationMatchRequest = {
  statement_row_id: number;
  match_type: ReconciliationMatchType;
  credit_account_name?: string;
  charge_subtype?: string;
};

export type ReconciliationMatchResponse = {
  statement_row_id: number;
  match_id: number;
  journal_entry_id: number | null;
  message: string;
  status: string;
};

export type ReconciliationUnmatchRequest = {
  statement_row_id: number;
  reason: string;
};

export type ReconciliationUnmatchResponse = {
  statement_row_id: number;
  message: string;
  status: string;
};

export type PeriodCloseResponse = {
  period_id: number;
  journal_entry_id: number;
  message: string;
  status: string;
};

export type ProfitAllocationRequest = {
  period_id: number;
  notes?: string;
};

export type ProfitAllocationResponse = {
  allocation_id: number;
  journal_entry_id: number | null;
  message: string;
  status: string;
};

export type AllocationVoidRequest = {
  reason: string;
};

export type AllocationVoidResponse = {
  allocation_id: number;
  journal_entry_id: number | null;
  message: string;
  status: string;
};
