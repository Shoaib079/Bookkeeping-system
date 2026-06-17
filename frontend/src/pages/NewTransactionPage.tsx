import { FormEvent, useMemo, useState } from "react";

import { BankAccountPicker } from "../components/BankAccountPicker";
import { CoaAccountPicker } from "../components/CoaAccountPicker";
import { FiscalPeriodPicker } from "../components/FiscalPeriodPicker";
import { PartnerPicker } from "../components/PartnerPicker";
import { ReadApiSetup } from "../components/ReadApiSetup";
import { StatementRowPicker } from "../components/StatementRowPicker";
import { VendorPicker } from "../components/VendorPicker";
import { WorkerPicker } from "../components/WorkerPicker";
import {
  reactWriteEnabled,
  reactWriteBankingEnabled,
  reactWriteClosingEnabled,
  reactWriteExpensesEnabled,
  reactWritePartnerWorkerEnabled,
  reactWritePurchasesEnabled,
  reactWriteReceivablePaymentsEnabled,
  reactWriteReconciliationEnabled,
  reactWriteSalesEnabled,
  reactWriteVoidsEnabled,
} from "../config/featureFlags";
import type { ApiError } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type {
  AllocationVoidResponse,
  CreateBankTransactionResponse,
  CreateExpenseResponse,
  CreatePartnerMovementResponse,
  CreatePurchaseResponse,
  CreateReceivablePaymentResponse,
  CreateSaleResponse,
  CreateWorkerPaymentResponse,
  PartnerMovementType,
  PeriodCloseResponse,
  ProfitAllocationResponse,
  ReconciliationMatchRequest,
  ReconciliationMatchResponse,
  ReconciliationMatchType,
  ReconciliationUnmatchResponse,
  VoidResponse,
  VoidTargetType,
  WorkerMovementType,
} from "../lib/api/types";
import { apiPost } from "../lib/api/writeClient";

type WriteTab =
  | "sale"
  | "expense"
  | "void"
  | "purchase"
  | "receivable"
  | "banking"
  | "partner"
  | "worker"
  | "reconcile"
  | "closing";
type ReconcileAction = "match" | "unmatch";
type ClosingAction = "close" | "allocate" | "voidAllocation";
type SalePaymentMethod = "Cash" | "Card" | "Credit";
type ExpensePaymentMethod = "Cash" | "Bank";
type PurchasePaymentMethod = "Cash" | "Bank" | "Credit";
type ReceivablePaymentMethod = "Cash" | "Bank";
type BankTransactionType = "deposit" | "withdrawal" | "transfer";

const CREDIT_CUSTOMER_MSG =
  "Enter a customer name for on-account (credit) sales.";

const VOID_REASON_MSG = "Void reason is required.";
const VENDOR_REQUIRED_MSG = "Select a vendor before saving a purchase.";
const CATEGORY_REQUIRED_MSG = "Select a category before saving";
const PURCHASE_BANK_MSG = "No bank account selected.";
const RECEIVABLE_BANK_MSG = "No bank account selected.";
const CARD_BANK_MSG = "No bank account selected.";
const BANK_TRANSFER_DEST_MSG =
  "Choose a different destination account for transfer.";
const PARTNER_AMOUNT_MSG = "Amount must be greater than zero.";
const PARTNER_BANK_MSG = "Bank account not found.";
const WORKER_BANK_MSG = "Bank account not found.";

function todayIso(): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function parseAmount(raw: string): number | null {
  const parsed = Number(raw.replace(/,/g, ""));
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

function parsePositiveInt(raw: string): number | null {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return null;
  }
  return Math.trunc(parsed);
}

function parseCommaSeparatedIds(raw: string): number[] | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  const ids: number[] = [];
  for (const part of trimmed.split(",")) {
    const piece = part.trim();
    if (!piece) {
      continue;
    }
    const parsed = Number(piece);
    if (!Number.isFinite(parsed) || parsed < 1) {
      return null;
    }
    ids.push(Math.trunc(parsed));
  }
  return ids.length ? ids : null;
}

type ReconPartnerMovementType =
  | "CapitalContribution"
  | "Drawing"
  | "Salary"
  | "Advance"
  | "Repayment";

type ReconWorkerMovementType = "Salary" | "Advance";

export function NewTransactionPage() {
  const salesOn = reactWriteSalesEnabled();
  const expensesOn = reactWriteExpensesEnabled();
  const voidsOn = reactWriteVoidsEnabled();
  const purchasesOn = reactWritePurchasesEnabled();
  const receivableOn = reactWriteReceivablePaymentsEnabled();
  const bankingOn = reactWriteBankingEnabled();
  const partnerWorkerOn = reactWritePartnerWorkerEnabled();
  const reconcileOn = reactWriteReconciliationEnabled();
  const closingOn = reactWriteClosingEnabled();
  const defaultTab: WriteTab = salesOn
    ? "sale"
    : expensesOn
      ? "expense"
      : purchasesOn
        ? "purchase"
        : receivableOn
          ? "receivable"
          : bankingOn
            ? "banking"
            : partnerWorkerOn
              ? "partner"
              : reconcileOn
                ? "reconcile"
                : closingOn
                  ? "closing"
                  : "void";

  const [sessionTick, setSessionTick] = useState(0);
  const session = useMemo(() => getReadSession(), [sessionTick]);
  const [tab, setTab] = useState<WriteTab>(defaultTab);
  const [date, setDate] = useState(todayIso());
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("TRY");
  const [notes, setNotes] = useState("");
  const [salePaymentMethod, setSalePaymentMethod] =
    useState<SalePaymentMethod>("Cash");
  const [customerName, setCustomerName] = useState("");
  const [cardBankAccountId, setCardBankAccountId] = useState("");
  const [expensePaymentMethod, setExpensePaymentMethod] =
    useState<ExpensePaymentMethod>("Cash");
  const [bankAccountId, setBankAccountId] = useState("");
  const [categoryName, setCategoryName] = useState("Office");
  const [subcategoryName, setSubcategoryName] = useState("Other");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saleResult, setSaleResult] = useState<CreateSaleResponse | null>(null);
  const [expenseResult, setExpenseResult] = useState<CreateExpenseResponse | null>(
    null,
  );
  const [voidTargetType, setVoidTargetType] = useState<VoidTargetType>("Sale");
  const [voidTargetId, setVoidTargetId] = useState("");
  const [voidReason, setVoidReason] = useState("");
  const [voidResult, setVoidResult] = useState<VoidResponse | null>(null);
  const [purchasePaymentMethod, setPurchasePaymentMethod] =
    useState<PurchasePaymentMethod>("Cash");
  const [vendorName, setVendorName] = useState("Acme Supplies");
  const [purchaseCategoryName, setPurchaseCategoryName] = useState("Inventory");
  const [purchaseSubcategoryName, setPurchaseSubcategoryName] =
    useState("General Stock");
  const [purchaseBankAccountId, setPurchaseBankAccountId] = useState("");
  const [purchaseResult, setPurchaseResult] = useState<CreatePurchaseResponse | null>(
    null,
  );
  const [receivablePaymentMethod, setReceivablePaymentMethod] =
    useState<ReceivablePaymentMethod>("Cash");
  const [receivableSaleId, setReceivableSaleId] = useState("");
  const [receivableCustomerName, setReceivableCustomerName] = useState("");
  const [receivableBankAccountId, setReceivableBankAccountId] = useState("");
  const [receivableResult, setReceivableResult] =
    useState<CreateReceivablePaymentResponse | null>(null);
  const [bankTransactionType, setBankTransactionType] =
    useState<BankTransactionType>("deposit");
  const [bankingAccountId, setBankingAccountId] = useState("");
  const [bankingDestinationAccountId, setBankingDestinationAccountId] = useState("");
  const [bankingCurrency, setBankingCurrency] = useState("");
  const [bankingResult, setBankingResult] =
    useState<CreateBankTransactionResponse | null>(null);
  const [partnerId, setPartnerId] = useState("");
  const [partnerMovementType, setPartnerMovementType] =
    useState<PartnerMovementType>("CapitalContribution");
  const [partnerBankAccountId, setPartnerBankAccountId] = useState("");
  const [partnerResult, setPartnerResult] =
    useState<CreatePartnerMovementResponse | null>(null);
  const [workerId, setWorkerId] = useState("");
  const [workerMovementType, setWorkerMovementType] =
    useState<WorkerMovementType>("Advance");
  const [workerBankAccountId, setWorkerBankAccountId] = useState("");
  const [workerGrossSalary, setWorkerGrossSalary] = useState("");
  const [workerDeductions, setWorkerDeductions] = useState("");
  const [workerAdvanceRecovery, setWorkerAdvanceRecovery] = useState("");
  const [workerPayPeriod, setWorkerPayPeriod] = useState("");
  const [workerResult, setWorkerResult] =
    useState<CreateWorkerPaymentResponse | null>(null);
  const [reconcileAction, setReconcileAction] = useState<ReconcileAction>("match");
  const [statementRowId, setStatementRowId] = useState("");
  const [reconMatchType, setReconMatchType] =
    useState<ReconciliationMatchType>("generic_deposit");
  const [reconCoaAccountId, setReconCoaAccountId] = useState("");
  const [reconCreditAccountName, setReconCreditAccountName] = useState("Sales Revenue");
  const [reconChargeSubtype, setReconChargeSubtype] = useState("");
  const [reconSaleIds, setReconSaleIds] = useState("");
  const [reconSettlementRowId, setReconSettlementRowId] = useState("");
  const [reconConfirmInferredFee, setReconConfirmInferredFee] = useState(false);
  const [reconVendorId, setReconVendorId] = useState("");
  const [reconPayableId, setReconPayableId] = useState("");
  const [reconExpenseCategory, setReconExpenseCategory] = useState("Office Expense");
  const [reconCreateExpense, setReconCreateExpense] = useState(false);
  const [reconPartnerId, setReconPartnerId] = useState("");
  const [reconPartnerMovementType, setReconPartnerMovementType] =
    useState<ReconPartnerMovementType>("CapitalContribution");
  const [reconWorkerId, setReconWorkerId] = useState("");
  const [reconWorkerMovementType, setReconWorkerMovementType] =
    useState<ReconWorkerMovementType>("Advance");
  const [reconGrossSalary, setReconGrossSalary] = useState("");
  const [reconDeductions, setReconDeductions] = useState("");
  const [reconAdvanceRecovery, setReconAdvanceRecovery] = useState("");
  const [reconPayPeriod, setReconPayPeriod] = useState("");
  const [reconEquityKind, setReconEquityKind] = useState("owner_capital");
  const [reconCreditCardAccountId, setReconCreditCardAccountId] = useState("");
  const [reconUnmatchReason, setReconUnmatchReason] = useState("");
  const [reconMatchResult, setReconMatchResult] =
    useState<ReconciliationMatchResponse | null>(null);
  const [reconUnmatchResult, setReconUnmatchResult] =
    useState<ReconciliationUnmatchResponse | null>(null);
  const [closingAction, setClosingAction] = useState<ClosingAction>("close");
  const [closingPeriodId, setClosingPeriodId] = useState("");
  const [closingAllocationId, setClosingAllocationId] = useState("");
  const [closingVoidReason, setClosingVoidReason] = useState("");
  const [closingNotes, setClosingNotes] = useState("");
  const [periodCloseResult, setPeriodCloseResult] =
    useState<PeriodCloseResponse | null>(null);
  const [allocationResult, setAllocationResult] =
    useState<ProfitAllocationResponse | null>(null);
  const [allocationVoidResult, setAllocationVoidResult] =
    useState<AllocationVoidResponse | null>(null);

  if (!reactWriteEnabled()) {
    return (
      <section className="erp-placeholder">
        <h1>New Transaction</h1>
        <p>
          Write UI disabled. Set <code>VITE_ERP_REACT_WRITE_SALES=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_EXPENSES=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_PURCHASES=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_BANKING=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_PARTNER_WORKER=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_RECONCILIATION=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_CLOSING=1</code>, and/or{" "}
          <code>VITE_ERP_REACT_WRITE_VOIDS=1</code>.
        </p>
      </section>
    );
  }

  async function handleSaleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedAmount = parseAmount(amount);
    if (parsedAmount === null) {
      setError("Enter a valid amount greater than zero.");
      return;
    }

    if (salePaymentMethod === "Credit") {
      const name = customerName.trim();
      if (!name || name === "Walk-in Customer") {
        setError(CREDIT_CUSTOMER_MSG);
        return;
      }
    }
    let cardAccount: number | undefined;
    if (salePaymentMethod === "Card") {
      const parsed = parsePositiveInt(cardBankAccountId);
      if (parsed === null) {
        setError(CARD_BANK_MSG);
        return;
      }
      cardAccount = parsed;
    }

    setLoading(true);
    setError(null);
    setSaleResult(null);
    try {
      const body: {
        date: string;
        amount: number;
        currency: string;
        payment_method: SalePaymentMethod;
        notes: string;
        customer_name?: string;
        card_bank_account_id?: number;
      } = {
        date,
        amount: parsedAmount,
        currency,
        payment_method: salePaymentMethod,
        notes: notes.trim(),
      };
      if (salePaymentMethod === "Credit") {
        body.customer_name = customerName.trim();
      }
      if (salePaymentMethod === "Card" && cardAccount !== undefined) {
        body.card_bank_account_id = cardAccount;
      }
      const response = await apiPost<CreateSaleResponse>(
        "/api/v1/sales",
        body,
        { session },
      );
      setSaleResult(response);
      setAmount("");
      setNotes("");
      setCustomerName("");
      setCardBankAccountId("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to save sale.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExpenseSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedAmount = parseAmount(amount);
    if (parsedAmount === null) {
      setError("Enter a valid amount greater than zero.");
      return;
    }
    const category = categoryName.trim();
    if (!category) {
      setError("Category name is required.");
      return;
    }
    let bankId: number | undefined;
    if (expensePaymentMethod === "Bank") {
      const parsed = parsePositiveInt(bankAccountId);
      if (parsed === null) {
        setError(RECEIVABLE_BANK_MSG);
        return;
      }
      bankId = parsed;
    }

    setLoading(true);
    setError(null);
    setExpenseResult(null);
    try {
      const body: {
        date: string;
        amount: number;
        currency: string;
        payment_method: ExpensePaymentMethod;
        notes: string;
        category_name: string;
        subcategory_name?: string;
        bank_account_id?: number;
      } = {
        date,
        amount: parsedAmount,
        currency,
        payment_method: expensePaymentMethod,
        notes: notes.trim(),
        category_name: category,
      };
      const sub = subcategoryName.trim();
      if (sub) {
        body.subcategory_name = sub;
      }
      if (expensePaymentMethod === "Bank" && bankId !== undefined) {
        body.bank_account_id = bankId;
      }
      const response = await apiPost<CreateExpenseResponse>(
        "/api/v1/expenses",
        body,
        { session },
      );
      setExpenseResult(response);
      setAmount("");
      setNotes("");
      setBankAccountId("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to save expense.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePurchaseSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedAmount = parseAmount(amount);
    if (parsedAmount === null) {
      setError("Enter a valid amount greater than zero.");
      return;
    }
    const vendor = vendorName.trim();
    if (!vendor) {
      setError(VENDOR_REQUIRED_MSG);
      return;
    }
    const category = purchaseCategoryName.trim();
    if (!category) {
      setError(CATEGORY_REQUIRED_MSG);
      return;
    }
    let bankId: number | undefined;
    if (purchasePaymentMethod === "Bank") {
      const parsed = parsePositiveInt(purchaseBankAccountId);
      if (parsed === null) {
        setError(PURCHASE_BANK_MSG);
        return;
      }
      bankId = parsed;
    }

    setLoading(true);
    setError(null);
    setPurchaseResult(null);
    try {
      const body: {
        date: string;
        amount: number;
        currency: string;
        payment_method: PurchasePaymentMethod;
        notes: string;
        vendor_name: string;
        category_name: string;
        subcategory_name?: string;
        bank_account_id?: number;
      } = {
        date,
        amount: parsedAmount,
        currency,
        payment_method: purchasePaymentMethod,
        notes: notes.trim(),
        vendor_name: vendor,
        category_name: category,
      };
      const sub = purchaseSubcategoryName.trim();
      if (sub) {
        body.subcategory_name = sub;
      }
      if (purchasePaymentMethod === "Bank" && bankId !== undefined) {
        body.bank_account_id = bankId;
      }
      const response = await apiPost<CreatePurchaseResponse>(
        "/api/v1/purchases",
        body,
        { session },
      );
      setPurchaseResult(response);
      setAmount("");
      setNotes("");
      setPurchaseBankAccountId("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to save purchase.");
    } finally {
      setLoading(false);
    }
  }

  async function handleReceivableSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedAmount = parseAmount(amount);
    if (parsedAmount === null) {
      setError("Enter a valid amount greater than zero.");
      return;
    }
    const saleId = parsePositiveInt(receivableSaleId);
    if (saleId === null) {
      setError("Enter a valid credit sale id.");
      return;
    }
    let bankId: number | undefined;
    if (receivablePaymentMethod === "Bank") {
      const parsed = parsePositiveInt(receivableBankAccountId);
      if (parsed === null) {
        setError(RECEIVABLE_BANK_MSG);
        return;
      }
      bankId = parsed;
    }

    setLoading(true);
    setError(null);
    setReceivableResult(null);
    try {
      const body: {
        date: string;
        amount: number;
        currency: string;
        payment_method: ReceivablePaymentMethod;
        sale_id: number;
        notes: string;
        customer_name?: string;
        bank_account_id?: number;
      } = {
        date,
        amount: parsedAmount,
        currency,
        payment_method: receivablePaymentMethod,
        sale_id: saleId,
        notes: notes.trim(),
      };
      const customer = receivableCustomerName.trim();
      if (customer) {
        body.customer_name = customer;
      }
      if (receivablePaymentMethod === "Bank" && bankId !== undefined) {
        body.bank_account_id = bankId;
      }
      const response = await apiPost<CreateReceivablePaymentResponse>(
        "/api/v1/receivable-payments",
        body,
        { session },
      );
      setReceivableResult(response);
      setAmount("");
      setNotes("");
      setReceivableBankAccountId("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to record receivable payment.");
    } finally {
      setLoading(false);
    }
  }

  async function handleBankingSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedAmount = parseAmount(amount);
    if (parsedAmount === null) {
      setError("Enter a valid amount greater than zero.");
      return;
    }
    const sourceId = parsePositiveInt(bankingAccountId);
    if (sourceId === null) {
      setError(PURCHASE_BANK_MSG);
      return;
    }
    let destinationId: number | undefined;
    if (bankTransactionType === "transfer") {
      const parsed = parsePositiveInt(bankingDestinationAccountId);
      if (parsed === null) {
        setError(BANK_TRANSFER_DEST_MSG);
        return;
      }
      if (parsed === sourceId) {
        setError(BANK_TRANSFER_DEST_MSG);
        return;
      }
      destinationId = parsed;
    }

    setLoading(true);
    setError(null);
    setBankingResult(null);
    try {
      const body: {
        date: string;
        amount: number;
        transaction_type: BankTransactionType;
        bank_account_id: number;
        notes: string;
        destination_bank_account_id?: number;
        currency?: string;
      } = {
        date,
        amount: parsedAmount,
        transaction_type: bankTransactionType,
        bank_account_id: sourceId,
        notes: notes.trim(),
      };
      if (bankTransactionType === "transfer" && destinationId !== undefined) {
        body.destination_bank_account_id = destinationId;
      }
      const currencyOverride = bankingCurrency.trim().toUpperCase();
      if (currencyOverride) {
        body.currency = currencyOverride;
      }
      const response = await apiPost<CreateBankTransactionResponse>(
        "/api/v1/bank-transactions",
        body,
        { session },
      );
      setBankingResult(response);
      setAmount("");
      setNotes("");
      setBankingDestinationAccountId("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to record bank transaction.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePartnerSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedPartnerId = parsePositiveInt(partnerId);
    if (parsedPartnerId === null) {
      setError("Select a partner.");
      return;
    }
    const parsedAmount = parseAmount(amount);
    if (parsedAmount === null) {
      setError(PARTNER_AMOUNT_MSG);
      return;
    }
    let bankId: number | undefined;
    if (partnerMovementType !== "AdvanceOffset") {
      const parsed = parsePositiveInt(partnerBankAccountId);
      if (parsed === null) {
        setError(PARTNER_BANK_MSG);
        return;
      }
      bankId = parsed;
    }

    setLoading(true);
    setError(null);
    setPartnerResult(null);
    try {
      const body: {
        partner_id: number;
        movement_type: PartnerMovementType;
        amount: number;
        date: string;
        notes?: string;
        bank_account_id?: number;
      } = {
        partner_id: parsedPartnerId,
        movement_type: partnerMovementType,
        amount: parsedAmount,
        date,
      };
      const trimmedNotes = notes.trim();
      if (trimmedNotes) {
        body.notes = trimmedNotes;
      }
      if (bankId !== undefined) {
        body.bank_account_id = bankId;
      }
      const response = await apiPost<CreatePartnerMovementResponse>(
        "/api/v1/partner-movements",
        body,
        { session },
      );
      setPartnerResult(response);
      setAmount("");
      setNotes("");
      setPartnerBankAccountId("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to save partner movement.");
    } finally {
      setLoading(false);
    }
  }

  async function handleWorkerSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const parsedWorkerId = parsePositiveInt(workerId);
    if (parsedWorkerId === null) {
      setError("Select a worker.");
      return;
    }
    const parsedBank = parsePositiveInt(workerBankAccountId);
    if (parsedBank === null) {
      setError(WORKER_BANK_MSG);
      return;
    }

    setLoading(true);
    setError(null);
    setWorkerResult(null);
    try {
      const body: {
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
      } = {
        worker_id: parsedWorkerId,
        movement_type: workerMovementType,
        date,
        bank_account_id: parsedBank,
      };
      if (workerMovementType === "Salary") {
        const gross = parseAmount(workerGrossSalary);
        if (gross === null) {
          setError("Enter a valid gross salary greater than zero.");
          setLoading(false);
          return;
        }
        body.gross_salary = gross;
        const deductions = parseAmount(workerDeductions);
        if (deductions !== null) {
          body.deductions = deductions;
        }
        const recovery = parseAmount(workerAdvanceRecovery);
        if (recovery !== null) {
          body.advance_recovery = recovery;
        }
        const period = workerPayPeriod.trim();
        if (period) {
          body.pay_period = period;
        }
      } else {
        const parsedAmount = parseAmount(amount);
        if (parsedAmount === null) {
          setError(PARTNER_AMOUNT_MSG);
          setLoading(false);
          return;
        }
        body.amount = parsedAmount;
      }
      const trimmedNotes = notes.trim();
      if (trimmedNotes) {
        body.notes = trimmedNotes;
      }
      const response = await apiPost<CreateWorkerPaymentResponse>(
        "/api/v1/worker-payments",
        body,
        { session },
      );
      setWorkerResult(response);
      setAmount("");
      setNotes("");
      setWorkerGrossSalary("");
      setWorkerDeductions("");
      setWorkerAdvanceRecovery("");
      setWorkerPayPeriod("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to save worker payment.");
    } finally {
      setLoading(false);
    }
  }

  async function handleReconcileSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const rowId = parsePositiveInt(statementRowId);
    if (rowId === null) {
      setError("Select a statement row.");
      return;
    }

    setLoading(true);
    setError(null);
    setReconMatchResult(null);
    setReconUnmatchResult(null);
    try {
      if (reconcileAction === "match") {
        const body: ReconciliationMatchRequest = {
          statement_row_id: rowId,
          match_type: reconMatchType,
        };
        if (reconMatchType === "generic_deposit") {
          const creditAccount = reconCreditAccountName.trim();
          if (!creditAccount) {
            setError("Select a credit account for generic deposit.");
            setLoading(false);
            return;
          }
          body.credit_account_name = creditAccount;
        } else if (reconMatchType === "bank_charge") {
          const subtype = reconChargeSubtype.trim();
          if (subtype) {
            body.charge_subtype = subtype;
          }
        } else if (reconMatchType === "deposit_clearing") {
          const saleIds = parseCommaSeparatedIds(reconSaleIds);
          if (saleIds === null) {
            setError("Enter one or more sale ids (comma-separated).");
            setLoading(false);
            return;
          }
          body.sale_ids = saleIds;
          const settlementId = parsePositiveInt(reconSettlementRowId);
          if (settlementId !== null) {
            body.settlement_row_id = settlementId;
          }
          if (reconConfirmInferredFee) {
            body.confirm_inferred_fee = true;
          }
        } else if (reconMatchType === "vendor_outflow") {
          const vendorId = parsePositiveInt(reconVendorId);
          if (vendorId === null) {
            setError("Select a vendor.");
            setLoading(false);
            return;
          }
          body.vendor_id = vendorId;
          const payableId = parsePositiveInt(reconPayableId);
          if (payableId !== null) {
            body.payable_id = payableId;
          }
          const category = reconExpenseCategory.trim();
          if (category) {
            body.expense_category = category;
          }
          if (reconCreateExpense) {
            body.create_expense = true;
          }
        } else if (reconMatchType === "partner") {
          const partnerId = parsePositiveInt(reconPartnerId);
          if (partnerId === null) {
            setError("Select a partner.");
            setLoading(false);
            return;
          }
          body.partner_id = partnerId;
          body.movement_type = reconPartnerMovementType;
        } else if (reconMatchType === "worker") {
          const workerId = parsePositiveInt(reconWorkerId);
          if (workerId === null) {
            setError("Select a worker.");
            setLoading(false);
            return;
          }
          body.worker_id = workerId;
          body.movement_type = reconWorkerMovementType;
          if (reconWorkerMovementType === "Salary") {
            const gross = parseAmount(reconGrossSalary);
            if (gross === null) {
              setError("Enter a valid gross salary greater than zero.");
              setLoading(false);
              return;
            }
            body.gross_salary = gross;
            const deductions = parseAmount(reconDeductions);
            if (deductions !== null) {
              body.deductions = deductions;
            }
            const recovery = parseAmount(reconAdvanceRecovery);
            if (recovery !== null) {
              body.advance_recovery = recovery;
            }
            const payPeriod = reconPayPeriod.trim();
            if (payPeriod) {
              body.pay_period = payPeriod;
            }
          }
        } else if (reconMatchType === "equity") {
          body.equity_kind = reconEquityKind;
        } else if (reconMatchType === "cc_bill_payment") {
          const cardAccountId = parsePositiveInt(reconCreditCardAccountId);
          if (cardAccountId === null) {
            setError("Select a credit card account.");
            setLoading(false);
            return;
          }
          body.credit_card_account_id = cardAccountId;
        }
        const response = await apiPost<ReconciliationMatchResponse>(
          "/api/v1/reconciliation/match",
          body,
          { session },
        );
        setReconMatchResult(response);
      } else {
        const reason = reconUnmatchReason.trim();
        if (!reason) {
          setError(VOID_REASON_MSG);
          setLoading(false);
          return;
        }
        const response = await apiPost<ReconciliationUnmatchResponse>(
          "/api/v1/reconciliation/unmatch",
          {
            statement_row_id: rowId,
            reason,
          },
          { session },
        );
        setReconUnmatchResult(response);
        setReconUnmatchReason("");
      }
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to post reconciliation action.");
    } finally {
      setLoading(false);
    }
  }

  async function handleClosingSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }

    setLoading(true);
    setError(null);
    setPeriodCloseResult(null);
    setAllocationResult(null);
    setAllocationVoidResult(null);
    try {
      if (closingAction === "close") {
        const periodId = parsePositiveInt(closingPeriodId);
        if (periodId === null) {
          setError("Select a fiscal period.");
          setLoading(false);
          return;
        }
        const response = await apiPost<PeriodCloseResponse>(
          `/api/v1/periods/${periodId}/close`,
          {},
          { session },
        );
        setPeriodCloseResult(response);
      } else if (closingAction === "allocate") {
        const periodId = parsePositiveInt(closingPeriodId);
        if (periodId === null) {
          setError("Select a fiscal period.");
          setLoading(false);
          return;
        }
        const body: { period_id: number; notes?: string } = { period_id: periodId };
        const trimmedNotes = closingNotes.trim();
        if (trimmedNotes) {
          body.notes = trimmedNotes;
        }
        const response = await apiPost<ProfitAllocationResponse>(
          "/api/v1/profit-allocations",
          body,
          { session },
        );
        setAllocationResult(response);
      } else {
        const allocationId = parsePositiveInt(closingAllocationId);
        if (allocationId === null) {
          setError("Enter a valid allocation id.");
          setLoading(false);
          return;
        }
        const reason = closingVoidReason.trim();
        if (!reason) {
          setError(VOID_REASON_MSG);
          setLoading(false);
          return;
        }
        const response = await apiPost<AllocationVoidResponse>(
          `/api/v1/profit-allocations/${allocationId}/void`,
          { reason },
          { session },
        );
        setAllocationVoidResult(response);
        setClosingVoidReason("");
      }
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to post closing action.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVoidSubmit(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      setError("Save a read API session before posting.");
      return;
    }
    const targetId = parsePositiveInt(voidTargetId);
    if (targetId === null) {
      setError("Enter a valid target id.");
      return;
    }
    const reason = voidReason.trim();
    if (!reason) {
      setError(VOID_REASON_MSG);
      return;
    }

    setLoading(true);
    setError(null);
    setVoidResult(null);
    try {
      const response = await apiPost<VoidResponse>(
        "/api/v1/voids",
        {
          target_type: voidTargetType,
          target_id: targetId,
          reason,
        },
        { session },
      );
      setVoidResult(response);
      setVoidTargetId("");
      setVoidReason("");
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.detail ?? "Failed to void record.");
    } finally {
      setLoading(false);
    }
  }

  function switchTab(next: WriteTab) {
    setTab(next);
    setError(null);
    setSaleResult(null);
    setExpenseResult(null);
    setVoidResult(null);
    setPurchaseResult(null);
    setReceivableResult(null);
    setBankingResult(null);
    setPartnerResult(null);
    setWorkerResult(null);
    setReconMatchResult(null);
    setReconUnmatchResult(null);
    setPeriodCloseResult(null);
    setAllocationResult(null);
    setAllocationVoidResult(null);
  }

  return (
    <section className="erp-write-page">
      <header className="erp-page-header">
        <h1>New Transaction</h1>
        <p className="erp-page-header__meta">
          Write tabs call existing P2 APIs (requires matching{" "}
          <code>ERP_API_WRITE_*</code> server flags).
        </p>
      </header>

      {!session ? (
        <ReadApiSetup onSaved={() => setSessionTick((v) => v + 1)} />
      ) : null}

      <nav className="erp-write-tabs" aria-label="Transaction type">
        {salesOn ? (
          <button
            type="button"
            className={tab === "sale" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"}
            onClick={() => switchTab("sale")}
          >
            Sale
          </button>
        ) : null}
        {expensesOn ? (
          <button
            type="button"
            className={
              tab === "expense" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"
            }
            onClick={() => switchTab("expense")}
          >
            Expense
          </button>
        ) : null}
        {voidsOn ? (
          <button
            type="button"
            className={tab === "void" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"}
            onClick={() => switchTab("void")}
          >
            Void
          </button>
        ) : null}
        {purchasesOn ? (
          <button
            type="button"
            className={
              tab === "purchase" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"
            }
            onClick={() => switchTab("purchase")}
          >
            Purchase
          </button>
        ) : null}
        {receivableOn ? (
          <button
            type="button"
            className={
              tab === "receivable" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"
            }
            onClick={() => switchTab("receivable")}
          >
            Receivable
          </button>
        ) : null}
        {bankingOn ? (
          <button
            type="button"
            className={
              tab === "banking" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"
            }
            onClick={() => switchTab("banking")}
          >
            Banking
          </button>
        ) : null}
        {partnerWorkerOn ? (
          <button
            type="button"
            className={
              tab === "partner" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"
            }
            onClick={() => switchTab("partner")}
          >
            Partner
          </button>
        ) : null}
        {partnerWorkerOn ? (
          <button
            type="button"
            className={
              tab === "worker" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"
            }
            onClick={() => switchTab("worker")}
          >
            Worker
          </button>
        ) : null}
        {reconcileOn ? (
          <button
            type="button"
            className={
              tab === "reconcile" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"
            }
            onClick={() => switchTab("reconcile")}
          >
            Reconcile
          </button>
        ) : null}
        {closingOn ? (
          <button
            type="button"
            className={
              tab === "closing" ? "erp-write-tabs__btn active" : "erp-write-tabs__btn"
            }
            onClick={() => switchTab("closing")}
          >
            Closing
          </button>
        ) : null}
      </nav>

      {tab === "sale" && salesOn ? (
        <form className="erp-write-form" onSubmit={handleSaleSubmit}>
          <label>
            Payment method
            <select
              value={salePaymentMethod}
              onChange={(event) =>
                setSalePaymentMethod(event.target.value as SalePaymentMethod)
              }
            >
              <option value="Cash">Cash</option>
              <option value="Card">Card</option>
              <option value="Credit">Credit</option>
            </select>
          </label>
          {salePaymentMethod === "Credit" ? (
            <label>
              Customer name
              <input
                type="text"
                value={customerName}
                onChange={(event) => setCustomerName(event.target.value)}
                required
              />
            </label>
          ) : null}
          {salePaymentMethod === "Card" ? (
            <BankAccountPicker
              label="Card bank account"
              value={cardBankAccountId}
              onChange={setCardBankAccountId}
              session={session}
              disabled={loading}
              excludeCreditCard
            />
          ) : null}
          <label>
            Date
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              required
            />
          </label>
          <label>
            Amount
            <input
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="0.00"
              required
            />
          </label>
          <label>
            Currency
            <input
              type="text"
              value={currency}
              onChange={(event) => setCurrency(event.target.value.toUpperCase())}
              maxLength={3}
              required
            />
          </label>
          <label>
            Notes
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </label>
          <button type="submit" disabled={!session || loading}>
            {loading ? "Saving…" : `Save ${salePaymentMethod.toLowerCase()} sale`}
          </button>
        </form>
      ) : null}

      {tab === "expense" && expensesOn ? (
        <form className="erp-write-form" onSubmit={handleExpenseSubmit}>
          <label>
            Payment method
            <select
              value={expensePaymentMethod}
              onChange={(event) =>
                setExpensePaymentMethod(event.target.value as ExpensePaymentMethod)
              }
            >
              <option value="Cash">Cash</option>
              <option value="Bank">Bank</option>
            </select>
          </label>
          {expensePaymentMethod === "Bank" ? (
            <BankAccountPicker
              value={bankAccountId}
              onChange={setBankAccountId}
              session={session}
              disabled={loading}
            />
          ) : null}
          <label>
            Date
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              required
            />
          </label>
          <label>
            Amount
            <input
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="0.00"
              required
            />
          </label>
          <label>
            Currency
            <input
              type="text"
              value={currency}
              onChange={(event) => setCurrency(event.target.value.toUpperCase())}
              maxLength={3}
              required
            />
          </label>
          <label>
            Category
            <input
              type="text"
              value={categoryName}
              onChange={(event) => setCategoryName(event.target.value)}
              required
            />
          </label>
          <label>
            Subcategory
            <input
              type="text"
              value={subcategoryName}
              onChange={(event) => setSubcategoryName(event.target.value)}
            />
          </label>
          <label>
            Notes
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </label>
          <button type="submit" disabled={!session || loading}>
            {loading ? "Saving…" : `Save ${expensePaymentMethod.toLowerCase()} expense`}
          </button>
        </form>
      ) : null}

      {tab === "purchase" && purchasesOn ? (
        <form className="erp-write-form" onSubmit={handlePurchaseSubmit}>
          <label>
            Payment method
            <select
              value={purchasePaymentMethod}
              onChange={(event) =>
                setPurchasePaymentMethod(event.target.value as PurchasePaymentMethod)
              }
            >
              <option value="Cash">Cash</option>
              <option value="Bank">Bank</option>
              <option value="Credit">Credit</option>
            </select>
          </label>
          {purchasePaymentMethod === "Bank" ? (
            <BankAccountPicker
              value={purchaseBankAccountId}
              onChange={setPurchaseBankAccountId}
              session={session}
              disabled={loading}
            />
          ) : null}
          <label>
            Vendor name
            <input
              type="text"
              value={vendorName}
              onChange={(event) => setVendorName(event.target.value)}
              required
            />
          </label>
          <label>
            Date
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              required
            />
          </label>
          <label>
            Amount
            <input
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="0.00"
              required
            />
          </label>
          <label>
            Currency
            <input
              type="text"
              value={currency}
              onChange={(event) => setCurrency(event.target.value.toUpperCase())}
              maxLength={3}
              required
            />
          </label>
          <label>
            Category
            <input
              type="text"
              value={purchaseCategoryName}
              onChange={(event) => setPurchaseCategoryName(event.target.value)}
              required
            />
          </label>
          <label>
            Subcategory
            <input
              type="text"
              value={purchaseSubcategoryName}
              onChange={(event) => setPurchaseSubcategoryName(event.target.value)}
            />
          </label>
          <label>
            Notes
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </label>
          <button type="submit" disabled={!session || loading}>
            {loading ? "Saving…" : `Save ${purchasePaymentMethod.toLowerCase()} purchase`}
          </button>
        </form>
      ) : null}

      {tab === "receivable" && receivableOn ? (
        <form className="erp-write-form" onSubmit={handleReceivableSubmit}>
          <label>
            Payment method
            <select
              value={receivablePaymentMethod}
              onChange={(event) =>
                setReceivablePaymentMethod(
                  event.target.value as ReceivablePaymentMethod,
                )
              }
            >
              <option value="Cash">Cash</option>
              <option value="Bank">Bank</option>
            </select>
          </label>
          {receivablePaymentMethod === "Bank" ? (
            <BankAccountPicker
              value={receivableBankAccountId}
              onChange={setReceivableBankAccountId}
              session={session}
              disabled={loading}
            />
          ) : null}
          <label>
            Credit sale id
            <input
              type="number"
              min={1}
              value={receivableSaleId}
              onChange={(event) => setReceivableSaleId(event.target.value)}
              required
            />
          </label>
          <label>
            Customer name (optional)
            <input
              type="text"
              value={receivableCustomerName}
              onChange={(event) => setReceivableCustomerName(event.target.value)}
            />
          </label>
          <label>
            Date
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              required
            />
          </label>
          <label>
            Amount
            <input
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="0.00"
              required
            />
          </label>
          <label>
            Currency
            <input
              type="text"
              value={currency}
              onChange={(event) => setCurrency(event.target.value.toUpperCase())}
              maxLength={3}
              required
            />
          </label>
          <label>
            Notes
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </label>
          <button type="submit" disabled={!session || loading}>
            {loading
              ? "Saving…"
              : `Record ${receivablePaymentMethod.toLowerCase()} payment`}
          </button>
        </form>
      ) : null}

      {tab === "banking" && bankingOn ? (
        <form className="erp-write-form" onSubmit={handleBankingSubmit}>
          <label>
            Transaction type
            <select
              value={bankTransactionType}
              onChange={(event) =>
                setBankTransactionType(event.target.value as BankTransactionType)
              }
            >
              <option value="deposit">deposit</option>
              <option value="withdrawal">withdrawal</option>
              <option value="transfer">transfer</option>
            </select>
          </label>
          <BankAccountPicker
            value={bankingAccountId}
            onChange={setBankingAccountId}
            session={session}
            disabled={loading}
          />
          {bankTransactionType === "transfer" ? (
            <BankAccountPicker
              label="Destination bank account"
              value={bankingDestinationAccountId}
              onChange={setBankingDestinationAccountId}
              session={session}
              disabled={loading}
            />
          ) : null}
          <label>
            Date
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              required
            />
          </label>
          <label>
            Amount
            <input
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="0.00"
              required
            />
          </label>
          <label>
            Currency (optional)
            <input
              type="text"
              value={bankingCurrency}
              onChange={(event) => setBankingCurrency(event.target.value.toUpperCase())}
              maxLength={3}
              placeholder="Account default"
            />
          </label>
          <label>
            Notes
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </label>
          <button type="submit" disabled={!session || loading}>
            {loading ? "Saving…" : `Record ${bankTransactionType}`}
          </button>
        </form>
      ) : null}

      {tab === "partner" && partnerWorkerOn ? (
        <form className="erp-write-form" onSubmit={handlePartnerSubmit}>
          <PartnerPicker
            value={partnerId}
            onChange={setPartnerId}
            session={session}
            disabled={loading}
          />
          <label>
            Movement type
            <select
              value={partnerMovementType}
              onChange={(event) =>
                setPartnerMovementType(event.target.value as PartnerMovementType)
              }
            >
              <option value="CapitalContribution">CapitalContribution</option>
              <option value="Drawing">Drawing</option>
              <option value="Salary">Salary</option>
              <option value="Advance">Advance</option>
              <option value="Repayment">Repayment</option>
              <option value="AdvanceOffset">AdvanceOffset</option>
            </select>
          </label>
          {partnerMovementType !== "AdvanceOffset" ? (
            <BankAccountPicker
              value={partnerBankAccountId}
              onChange={setPartnerBankAccountId}
              session={session}
              disabled={loading}
            />
          ) : null}
          <label>
            Date
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              required
            />
          </label>
          <label>
            Amount
            <input
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="0.00"
              required
            />
          </label>
          <label>
            Notes
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </label>
          <button type="submit" disabled={!session || loading}>
            {loading ? "Saving…" : `Save ${partnerMovementType}`}
          </button>
        </form>
      ) : null}

      {tab === "worker" && partnerWorkerOn ? (
        <form className="erp-write-form" onSubmit={handleWorkerSubmit}>
          <WorkerPicker
            value={workerId}
            onChange={setWorkerId}
            session={session}
            disabled={loading}
          />
          <label>
            Movement type
            <select
              value={workerMovementType}
              onChange={(event) =>
                setWorkerMovementType(event.target.value as WorkerMovementType)
              }
            >
              <option value="Salary">Salary</option>
              <option value="Advance">Advance</option>
              <option value="Repayment">Repayment</option>
            </select>
          </label>
          <BankAccountPicker
            value={workerBankAccountId}
            onChange={setWorkerBankAccountId}
            session={session}
            disabled={loading}
          />
          {workerMovementType === "Salary" ? (
            <>
              <label>
                Gross salary
                <input
                  type="text"
                  inputMode="decimal"
                  value={workerGrossSalary}
                  onChange={(event) => setWorkerGrossSalary(event.target.value)}
                  placeholder="0.00"
                  required
                />
              </label>
              <label>
                Deductions (optional)
                <input
                  type="text"
                  inputMode="decimal"
                  value={workerDeductions}
                  onChange={(event) => setWorkerDeductions(event.target.value)}
                  placeholder="0.00"
                />
              </label>
              <label>
                Advance recovery (optional)
                <input
                  type="text"
                  inputMode="decimal"
                  value={workerAdvanceRecovery}
                  onChange={(event) => setWorkerAdvanceRecovery(event.target.value)}
                  placeholder="0.00"
                />
              </label>
              <label>
                Pay period (optional)
                <input
                  type="text"
                  value={workerPayPeriod}
                  onChange={(event) => setWorkerPayPeriod(event.target.value)}
                />
              </label>
            </>
          ) : (
            <label>
              Amount
              <input
                type="text"
                inputMode="decimal"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0.00"
                required
              />
            </label>
          )}
          <label>
            Date
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              required
            />
          </label>
          <label>
            Notes
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </label>
          <button type="submit" disabled={!session || loading}>
            {loading ? "Saving…" : `Save ${workerMovementType}`}
          </button>
        </form>
      ) : null}

      {tab === "reconcile" && reconcileOn ? (
        <form className="erp-write-form" onSubmit={handleReconcileSubmit}>
          <label>
            Action
            <select
              value={reconcileAction}
              onChange={(event) =>
                setReconcileAction(event.target.value as ReconcileAction)
              }
            >
              <option value="match">Match</option>
              <option value="unmatch">Unmatch</option>
            </select>
          </label>
          <StatementRowPicker
            value={statementRowId}
            onChange={setStatementRowId}
            session={session}
            disabled={loading}
          />
          {reconcileAction === "match" ? (
            <>
              <label>
                Match type
                <select
                  value={reconMatchType}
                  onChange={(event) =>
                    setReconMatchType(event.target.value as ReconciliationMatchType)
                  }
                >
                  <option value="generic_deposit">generic_deposit</option>
                  <option value="bank_charge">bank_charge</option>
                  <option value="deposit_clearing">deposit_clearing</option>
                  <option value="vendor_outflow">vendor_outflow</option>
                  <option value="partner">partner</option>
                  <option value="worker">worker</option>
                  <option value="equity">equity</option>
                  <option value="cc_bill_payment">cc_bill_payment</option>
                </select>
              </label>
              {reconMatchType === "generic_deposit" ? (
                <CoaAccountPicker
                  label="Credit account"
                  value={reconCoaAccountId}
                  onChange={setReconCoaAccountId}
                  onAccountNameChange={setReconCreditAccountName}
                  session={session}
                  disabled={loading}
                />
              ) : null}
              {reconMatchType === "bank_charge" ? (
                <label>
                  Charge subtype (optional)
                  <select
                    value={reconChargeSubtype}
                    onChange={(event) => setReconChargeSubtype(event.target.value)}
                  >
                    <option value="">Infer from description</option>
                    <option value="interest">interest</option>
                    <option value="credit_card_fee">credit_card_fee</option>
                    <option value="card_settlement_fee">card_settlement_fee</option>
                    <option value="transfer_fee">transfer_fee</option>
                  </select>
                </label>
              ) : null}
              {reconMatchType === "deposit_clearing" ? (
                <>
                  <label>
                    Sale ids (comma-separated)
                    <input
                      type="text"
                      value={reconSaleIds}
                      onChange={(event) => setReconSaleIds(event.target.value)}
                      placeholder="1, 2, 3"
                      required
                    />
                  </label>
                  <label>
                    Settlement row id (optional)
                    <input
                      type="number"
                      min={1}
                      value={reconSettlementRowId}
                      onChange={(event) => setReconSettlementRowId(event.target.value)}
                    />
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={reconConfirmInferredFee}
                      onChange={(event) =>
                        setReconConfirmInferredFee(event.target.checked)
                      }
                    />{" "}
                    Confirm inferred fee
                  </label>
                </>
              ) : null}
              {reconMatchType === "vendor_outflow" ? (
                <>
                  <VendorPicker
                    value={reconVendorId}
                    onChange={setReconVendorId}
                    session={session}
                    disabled={loading}
                  />
                  <label>
                    Payable id (optional)
                    <input
                      type="number"
                      min={1}
                      value={reconPayableId}
                      onChange={(event) => setReconPayableId(event.target.value)}
                    />
                  </label>
                  <label>
                    Expense category
                    <input
                      type="text"
                      value={reconExpenseCategory}
                      onChange={(event) => setReconExpenseCategory(event.target.value)}
                    />
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={reconCreateExpense}
                      onChange={(event) => setReconCreateExpense(event.target.checked)}
                    />{" "}
                    Create expense record
                  </label>
                </>
              ) : null}
              {reconMatchType === "partner" ? (
                <>
                  <PartnerPicker
                    value={reconPartnerId}
                    onChange={setReconPartnerId}
                    session={session}
                    disabled={loading}
                  />
                  <label>
                    Movement type
                    <select
                      value={reconPartnerMovementType}
                      onChange={(event) =>
                        setReconPartnerMovementType(
                          event.target.value as ReconPartnerMovementType,
                        )
                      }
                    >
                      <option value="CapitalContribution">CapitalContribution</option>
                      <option value="Drawing">Drawing</option>
                      <option value="Salary">Salary</option>
                      <option value="Advance">Advance</option>
                      <option value="Repayment">Repayment</option>
                    </select>
                  </label>
                </>
              ) : null}
              {reconMatchType === "worker" ? (
                <>
                  <WorkerPicker
                    value={reconWorkerId}
                    onChange={setReconWorkerId}
                    session={session}
                    disabled={loading}
                  />
                  <label>
                    Movement type
                    <select
                      value={reconWorkerMovementType}
                      onChange={(event) =>
                        setReconWorkerMovementType(
                          event.target.value as ReconWorkerMovementType,
                        )
                      }
                    >
                      <option value="Salary">Salary</option>
                      <option value="Advance">Advance</option>
                    </select>
                  </label>
                  {reconWorkerMovementType === "Salary" ? (
                    <>
                      <label>
                        Gross salary
                        <input
                          type="text"
                          inputMode="decimal"
                          value={reconGrossSalary}
                          onChange={(event) => setReconGrossSalary(event.target.value)}
                          required
                        />
                      </label>
                      <label>
                        Deductions (optional)
                        <input
                          type="text"
                          inputMode="decimal"
                          value={reconDeductions}
                          onChange={(event) => setReconDeductions(event.target.value)}
                        />
                      </label>
                      <label>
                        Advance recovery (optional)
                        <input
                          type="text"
                          inputMode="decimal"
                          value={reconAdvanceRecovery}
                          onChange={(event) =>
                            setReconAdvanceRecovery(event.target.value)
                          }
                        />
                      </label>
                      <label>
                        Pay period (optional)
                        <input
                          type="text"
                          value={reconPayPeriod}
                          onChange={(event) => setReconPayPeriod(event.target.value)}
                        />
                      </label>
                    </>
                  ) : null}
                </>
              ) : null}
              {reconMatchType === "equity" ? (
                <label>
                  Equity kind
                  <select
                    value={reconEquityKind}
                    onChange={(event) => setReconEquityKind(event.target.value)}
                  >
                    <option value="owner_capital">owner_capital</option>
                    <option value="owner_drawing">owner_drawing</option>
                    <option value="loan_payment">loan_payment</option>
                    <option value="loan_receipt">loan_receipt</option>
                  </select>
                </label>
              ) : null}
              {reconMatchType === "cc_bill_payment" ? (
                <BankAccountPicker
                  label="Credit card account"
                  value={reconCreditCardAccountId}
                  onChange={setReconCreditCardAccountId}
                  session={session}
                  disabled={loading}
                  creditCardOnly
                />
              ) : null}
            </>
          ) : (
            <label>
              Unmatch reason
              <textarea
                value={reconUnmatchReason}
                onChange={(event) => setReconUnmatchReason(event.target.value)}
                rows={3}
                required
              />
            </label>
          )}
          <button type="submit" disabled={!session || loading}>
            {loading
              ? "Saving…"
              : reconcileAction === "match"
                ? "Match statement row"
                : "Unmatch statement row"}
          </button>
        </form>
      ) : null}

      {tab === "closing" && closingOn ? (
        <form className="erp-write-form" onSubmit={handleClosingSubmit}>
          <label>
            Action
            <select
              value={closingAction}
              onChange={(event) =>
                setClosingAction(event.target.value as ClosingAction)
              }
            >
              <option value="close">Close period</option>
              <option value="allocate">Profit allocation</option>
              <option value="voidAllocation">Void allocation</option>
            </select>
          </label>
          {closingAction === "voidAllocation" ? (
            <>
              <label>
                Allocation id
                <input
                  type="number"
                  min={1}
                  value={closingAllocationId}
                  onChange={(event) => setClosingAllocationId(event.target.value)}
                  required
                />
              </label>
              <label>
                Void reason
                <textarea
                  value={closingVoidReason}
                  onChange={(event) => setClosingVoidReason(event.target.value)}
                  rows={3}
                  required
                />
              </label>
            </>
          ) : (
            <>
              <FiscalPeriodPicker
                value={closingPeriodId}
                onChange={setClosingPeriodId}
                session={session}
                disabled={loading}
                openOnly={closingAction === "close"}
                closedOnly={closingAction === "allocate"}
              />
              {closingAction === "allocate" ? (
                <label>
                  Notes (optional)
                  <textarea
                    value={closingNotes}
                    onChange={(event) => setClosingNotes(event.target.value)}
                    rows={3}
                  />
                </label>
              ) : null}
            </>
          )}
          <button type="submit" disabled={!session || loading}>
            {loading
              ? "Saving…"
              : closingAction === "close"
                ? "Close period"
                : closingAction === "allocate"
                  ? "Allocate profit"
                  : "Void allocation"}
          </button>
        </form>
      ) : null}

      {tab === "void" && voidsOn ? (
        <form className="erp-write-form" onSubmit={handleVoidSubmit}>
          <label>
            Target type
            <select
              value={voidTargetType}
              onChange={(event) =>
                setVoidTargetType(event.target.value as VoidTargetType)
              }
            >
              <option value="Sale">Sale</option>
              <option value="ExpenseRecord">ExpenseRecord</option>
              <option value="Purchase">Purchase</option>
              <option value="Payable">Payable</option>
              <option value="BankTransaction">BankTransaction</option>
            </select>
          </label>
          <label>
            Target id
            <input
              type="number"
              min={1}
              value={voidTargetId}
              onChange={(event) => setVoidTargetId(event.target.value)}
              required
            />
          </label>
          <label>
            Void reason
            <textarea
              value={voidReason}
              onChange={(event) => setVoidReason(event.target.value)}
              rows={3}
              required
            />
          </label>
          <button type="submit" disabled={!session || loading}>
            {loading ? "Voiding…" : "Void record"}
          </button>
        </form>
      ) : null}

      {error ? <p className="erp-error">{error}</p> : null}
      {saleResult ? (
        <article className="erp-card erp-write-result">
          <h2>Sale saved</h2>
          <p>{saleResult.message}</p>
          <p className="erp-muted">
            Invoice {saleResult.invoice_number} · sale #{saleResult.sale_id}
          </p>
        </article>
      ) : null}
      {expenseResult ? (
        <article className="erp-card erp-write-result">
          <h2>Expense saved</h2>
          <p>{expenseResult.message}</p>
          <p className="erp-muted">Expense #{expenseResult.expense_id}</p>
        </article>
      ) : null}
      {voidResult ? (
        <article className="erp-card erp-write-result">
          <h2>Record voided</h2>
          <p>{voidResult.message}</p>
          <p className="erp-muted">
            {voidResult.target_type} #{voidResult.target_id}
            {voidResult.reversal_journal_entry_id
              ? ` · reversal JE #${voidResult.reversal_journal_entry_id}`
              : ""}
          </p>
        </article>
      ) : null}
      {purchaseResult ? (
        <article className="erp-card erp-write-result">
          <h2>Purchase saved</h2>
          <p>{purchaseResult.message}</p>
          <p className="erp-muted">
            Purchase #{purchaseResult.purchase_id}
            {purchaseResult.payable_id ? ` · payable #${purchaseResult.payable_id}` : ""}
          </p>
        </article>
      ) : null}
      {receivableResult ? (
        <article className="erp-card erp-write-result">
          <h2>Payment recorded</h2>
          <p>{receivableResult.message}</p>
          <p className="erp-muted">
            Sale #{receivableResult.sale_id} · payment #{receivableResult.payment_id}
          </p>
        </article>
      ) : null}
      {bankingResult ? (
        <article className="erp-card erp-write-result">
          <h2>Bank transaction saved</h2>
          <p>{bankingResult.message}</p>
          <p className="erp-muted">
            Bank tx #{bankingResult.bank_transaction_id}
            {bankingResult.paired_transaction_id
              ? ` · paired #${bankingResult.paired_transaction_id}`
              : ""}
          </p>
        </article>
      ) : null}
      {partnerResult ? (
        <article className="erp-card erp-write-result">
          <h2>Partner movement saved</h2>
          <p>{partnerResult.message}</p>
          <p className="erp-muted">Movement #{partnerResult.movement_id}</p>
        </article>
      ) : null}
      {workerResult ? (
        <article className="erp-card erp-write-result">
          <h2>Worker payment saved</h2>
          <p>{workerResult.message}</p>
          <p className="erp-muted">Payment #{workerResult.payment_id}</p>
        </article>
      ) : null}
      {reconMatchResult ? (
        <article className="erp-card erp-write-result">
          <h2>Statement row matched</h2>
          <p>{reconMatchResult.message}</p>
          <p className="erp-muted">
            Row #{reconMatchResult.statement_row_id} · match #{reconMatchResult.match_id}
          </p>
        </article>
      ) : null}
      {reconUnmatchResult ? (
        <article className="erp-card erp-write-result">
          <h2>Statement row unmatched</h2>
          <p>{reconUnmatchResult.message}</p>
          <p className="erp-muted">Row #{reconUnmatchResult.statement_row_id}</p>
        </article>
      ) : null}
      {periodCloseResult ? (
        <article className="erp-card erp-write-result">
          <h2>Period closed</h2>
          <p>{periodCloseResult.message}</p>
          <p className="erp-muted">Period #{periodCloseResult.period_id}</p>
        </article>
      ) : null}
      {allocationResult ? (
        <article className="erp-card erp-write-result">
          <h2>Profit allocated</h2>
          <p>{allocationResult.message}</p>
          <p className="erp-muted">Allocation #{allocationResult.allocation_id}</p>
        </article>
      ) : null}
      {allocationVoidResult ? (
        <article className="erp-card erp-write-result">
          <h2>Allocation voided</h2>
          <p>{allocationVoidResult.message}</p>
          <p className="erp-muted">Allocation #{allocationVoidResult.allocation_id}</p>
        </article>
      ) : null}
    </section>
  );
}
