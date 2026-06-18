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

export type BankStatementRowListItem = {
  id: number;
  import_row_index: number;
  date: string | null;
  description: string;
  amount: number;
  status: string;
  currency: string;
  bank_statement_import_id: number;
  company_id: number;
};

export type BankStatementRowsListResponse = {
  rows: BankStatementRowListItem[];
  row_count: number;
};

export type FiscalPeriodListRow = {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  is_closed: boolean;
  company_id: number;
};

export type FiscalPeriodsListResponse = {
  rows: FiscalPeriodListRow[];
  row_count: number;
};

export type YearEndCloseListRow = {
  id: number;
  fiscal_year: string;
  start_date: string;
  end_date: string;
  status: string;
  closed_by_name: string | null;
  closed_at: string;
  notes: string | null;
  period_count: number;
  allocation_count: number;
  net_income_snapshot: number;
  re_balance_at_close: number;
  is_void: boolean;
  voided_by_name: string | null;
  voided_at: string | null;
  void_reason: string | null;
  company_id: number;
};

export type YearEndClosesListResponse = {
  rows: YearEndCloseListRow[];
  row_count: number;
  company_id: number;
};

export type MyAccountCompanyRow = {
  company_id: number;
  company_name: string;
  role: string;
  is_default: boolean;
};

export type MyAccountResponse = {
  user_id: number;
  username: string;
  display_name: string | null;
  email: string | null;
  phone: string | null;
  company_role: string | null;
  active_company_id: number | null;
  active_company_name: string | null;
  member_since: string | null;
  last_login: string | null;
  companies: MyAccountCompanyRow[];
};

export type EodCloseListRow = {
  id: number;
  date: string;
  status: string;
  closed_by_name: string | null;
  closed_at: string;
  had_warnings: boolean;
  total_sales: number;
  total_expenses: number;
  net_cash_movement: number;
  recon_status: string | null;
  notes_preview: string | null;
  is_void: boolean;
  is_stale: boolean;
  company_id: number;
};

export type EodClosesListResponse = {
  rows: EodCloseListRow[];
  row_count: number;
  company_id: number;
  start_date: string | null;
  end_date: string | null;
};

export type CashReconciliationListRow = {
  id: number;
  date: string;
  cash_account_name: string | null;
  expected_cash: number;
  actual_cash: number;
  difference: number;
  variance_type: string;
  status: string;
  submitted_by_name: string | null;
  approved_by_name: string | null;
  journal_entry_id: number | null;
  is_void: boolean;
  company_id: number;
};

export type CashReconciliationsListResponse = {
  rows: CashReconciliationListRow[];
  row_count: number;
  company_id: number;
  start_date: string | null;
  end_date: string | null;
  status: string | null;
};

export type ExternalSalesVerificationListRow = {
  id: number;
  company_id: number;
  business_date: string;
  source_name: string;
  source_type: string | null;
  branch_location: string | null;
  status: string;
  external_total: number | null;
  z_report_total: number | null;
  external_cash: number | null;
  external_card: number | null;
  external_online: number | null;
  erp_total: number | null;
  erp_cash: number | null;
  erp_card: number | null;
  erp_credit: number | null;
  variance_total: number | null;
  variance_cash: number | null;
  variance_card: number | null;
  variance_online: number | null;
  z_report_variance: number | null;
  variance_type: string | null;
  within_tolerance: boolean | null;
  variance_acknowledged: boolean | null;
};

export type ExternalSalesVerificationsListResponse = {
  rows: ExternalSalesVerificationListRow[];
  row_count: number;
  company_id: number;
  start_date: string | null;
  end_date: string | null;
};

export type JournalEntryLineListRow = {
  id: number;
  account_id: number;
  account_code: string;
  account_name: string;
  debit: number;
  credit: number;
  company_id: number;
};

export type JournalEntryListRow = {
  id: number;
  entry_date: string;
  description: string;
  reference_type: string | null;
  reference_id: number | null;
  total_debit: number;
  total_credit: number;
  company_id: number;
  lines: JournalEntryLineListRow[];
};

export type JournalEntriesListResponse = {
  rows: JournalEntryListRow[];
  row_count: number;
};

export type VendorListRow = {
  id: number;
  name: string;
  is_active: boolean;
  company_id: number;
};

export type VendorsListResponse = {
  rows: VendorListRow[];
  row_count: number;
};

export type CustomerListRow = {
  id: number;
  name: string;
  contact: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  is_active: boolean;
  company_id: number;
};

export type CustomersListResponse = {
  rows: CustomerListRow[];
  row_count: number;
};

export type ProductListRow = {
  id: number;
  sku: string | null;
  name: string;
  category: string | null;
  subcategory: string | null;
  unit_of_measure: string | null;
  quantity: number;
  min_stock: number;
  stock_status: string;
  cost_price: number;
  unit_price: number;
  is_active: boolean;
  company_id: number;
};

export type ProductsListResponse = {
  rows: ProductListRow[];
  row_count: number;
  stats: {
    total: number;
    low_stock: number;
    out_of_stock: number;
  };
  company_id: number;
};

export type SalesListRow = {
  id: number;
  date: string;
  invoice_number: string;
  customer_name: string;
  description: string;
  amount: number;
  sale_type: string;
  paid_amount: number;
  balance: number;
  due_date: string | null;
  status: string;
  is_void: boolean;
  currency: string | null;
  company_id: number;
};

export type SalesListResponse = {
  rows: SalesListRow[];
  row_count: number;
};

export type ExpenseListRow = {
  id: number;
  date: string;
  expense_type: string;
  category: string | null;
  description: string;
  amount: number;
  payment_method: string | null;
  employee_name: string | null;
  is_void: boolean;
  currency: string | null;
  company_id: number;
};

export type ExpensesListResponse = {
  rows: ExpenseListRow[];
  row_count: number;
};

export type PurchaseListRow = {
  id: number;
  date: string;
  vendor_name: string;
  purchase_number: string | null;
  purchase_type: string;
  gl_debit: string;
  amount: number;
  description: string;
  is_void: boolean;
  currency: string | null;
  company_id: number;
};

export type PurchasesListResponse = {
  rows: PurchaseListRow[];
  row_count: number;
};

export type ReceivableSaleListRow = {
  id: number;
  invoice_number: string;
  customer_name: string;
  date: string;
  due_date: string | null;
  balance: number;
  status: string;
  currency: string | null;
  company_id: number;
};

export type ReceivableSalesListResponse = {
  rows: ReceivableSaleListRow[];
  row_count: number;
};

export type ProfitAllocationListRow = {
  id: number;
  fiscal_period_id: number;
  period_name: string;
  allocated_at: string;
  total_net_income: number;
  is_void: boolean;
  company_id: number;
};

export type ProfitAllocationsListResponse = {
  rows: ProfitAllocationListRow[];
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

export type TrialBalanceRow = {
  account_code: string;
  account_name: string;
  account_type: string;
  debit: number;
  credit: number;
};

export type TrialBalanceResponse = {
  rows: TrialBalanceRow[];
  total_debit: number;
  total_credit: number;
  gl_total_debit: number;
  gl_total_credit: number;
  gl_balanced: boolean;
  gl_difference: number;
  row_count: number;
};

export type BudgetVsActualRow = {
  account_id: number;
  account_code: string;
  account_name: string;
  budgeted: number;
  actual: number;
  variance: number;
  used_pct: number | null;
  status: string;
};

export type BudgetVsActualResponse = {
  year: number;
  month: number;
  month_start: string;
  month_end: string;
  rows: BudgetVsActualRow[];
  row_count: number;
  total_budgeted: number;
  total_actual: number;
  total_variance: number;
  company_id: number;
};

export type ReconHealthSectionResponse = {
  gl_balance: number;
  subledger_balance: number;
  difference: number;
  status: string;
};

export type ReconHealthBankRow = {
  account_id: number;
  name: string;
  currency: string | null;
  stored_balance: number;
  derived_balance: number;
  difference: number;
  status: string;
};

export type ReconHealthCoaDriftRow = {
  account_code: string;
  account_name: string;
  account_type: string;
  cached_balance: number;
  expected_balance: number;
  delta: number;
  status: string;
};

export type ReconHealthCreditCardResponse = {
  enabled: boolean;
  gl_balance: number;
  subledger_total: number;
  difference: number;
  status: string;
  cards: Array<{
    id: number;
    name: string;
    balance: number;
    currency: string | null;
    last_activity_date: string | null;
  }>;
};

export type ReconHealthResponse = {
  currency: string;
  accounts_receivable: ReconHealthSectionResponse;
  accounts_payable: ReconHealthSectionResponse;
  credit_card: ReconHealthCreditCardResponse | null;
  bank_accounts: ReconHealthBankRow[];
  coa_drift_rows: ReconHealthCoaDriftRow[];
  coa_cache_clean: boolean;
  company_id: number;
};

export type OpeningBalancesStatusResponse = {
  currency: string;
  obe_balance: number;
  obe_status: string;
  obe_account_exists: boolean;
  bank_rows: Array<{
    id: number;
    name: string;
    kind: string;
    currency: string | null;
    stored_balance: number;
    is_active: boolean;
    ob_posted: boolean;
    ob_date: string | null;
    ob_amount: number | null;
  }>;
  customer_rows: Array<{
    id: number;
    name: string;
    ob_posted: boolean;
    ob_date: string | null;
    ob_amount: number | null;
  }>;
  vendor_rows: Array<{
    id: number;
    name: string;
    ob_posted: boolean;
    ob_date: string | null;
    ob_amount: number | null;
  }>;
  product_rows: Array<{
    id: number;
    name: string;
    sku: string | null;
    quantity: number;
    ob_posted: boolean;
    ob_date: string | null;
    ob_cost: number | null;
  }>;
  capital: {
    ob_posted: boolean;
    ob_date: string | null;
    ob_amount: number | null;
  };
  loan_rows: Array<{
    journal_entry_id: number;
    entry_date: string;
    description: string;
    amount: number;
  }>;
  company_id: number;
};

export type AuditLogListRow = {
  id: number;
  timestamp: string;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  description: string;
  performed_by: string | null;
  company_id: number;
};

export type AuditLogListResponse = {
  rows: AuditLogListRow[];
  row_count: number;
  limit: number;
};

export type CompanyMemberRow = {
  membership_id: number;
  user_id: number;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
  last_login: string | null;
  invited_by: string;
  member_since: string | null;
  company_id: number;
};

export type CompanyMembersResponse = {
  rows: CompanyMemberRow[];
  row_count: number;
  stats: {
    total: number;
    active: number;
    inactive: number;
    by_role: Record<string, number>;
  };
  company_id: number;
};

export type PermissionMemberRow = {
  user_id: number;
  username: string;
  display_name: string;
  role: string;
  company_id: number;
};

export type PermissionMembersResponse = {
  rows: PermissionMemberRow[];
  row_count: number;
  company_id: number;
};

export type PermissionProvenanceRow = {
  permission_key: string;
  in_template: boolean;
  is_grant: boolean;
  is_deny: boolean;
  is_effective: boolean;
};

export type EffectivePermissionsResponse = {
  user_id: number;
  role: string | null;
  template_count: number;
  grant_count: number;
  deny_count: number;
  effective_count: number;
  rows: PermissionProvenanceRow[];
  company_id: number;
};

export type CompanySettingsResponse = {
  company_id: number;
  slug: string;
  display_name: string;
  legal_name: string | null;
  logo_url: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  tax_number: string | null;
  base_currency: string;
  tax_rate: number;
  fiscal_year_label: string;
  document_language: string;
  wizard_complete: boolean;
};

export type BackupFileRow = {
  name: string;
  size_kb: number;
  modified: string;
  has_uploads_zip: boolean;
};

export type BackupStatusResponse = {
  rows: BackupFileRow[];
  row_count: number;
  last_backup: string | null;
  db_size_kb: number;
  cloud_folder: string | null;
  cloud_folder_exists: boolean;
  company_id: number;
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
  sale_ids?: number[];
  settlement_row_id?: number;
  confirm_inferred_fee?: boolean;
  vendor_id?: number;
  payable_id?: number;
  expense_category?: string;
  create_expense?: boolean;
  partner_id?: number;
  movement_type?: string;
  worker_id?: number;
  gross_salary?: number;
  deductions?: number;
  advance_recovery?: number;
  pay_period?: string;
  equity_kind?: string;
  credit_card_account_id?: number;
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
