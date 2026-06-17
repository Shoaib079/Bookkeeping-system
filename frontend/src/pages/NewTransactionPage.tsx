import { FormEvent, useMemo, useState } from "react";

import { ReadApiSetup } from "../components/ReadApiSetup";
import {
  reactWriteEnabled,
  reactWriteBankingEnabled,
  reactWriteExpensesEnabled,
  reactWritePurchasesEnabled,
  reactWriteReceivablePaymentsEnabled,
  reactWriteSalesEnabled,
  reactWriteVoidsEnabled,
} from "../config/featureFlags";
import type { ApiError } from "../lib/api/client";
import { getReadSession } from "../lib/api/session";
import type {
  CreateBankTransactionResponse,
  CreateExpenseResponse,
  CreatePurchaseResponse,
  CreateReceivablePaymentResponse,
  CreateSaleResponse,
  VoidResponse,
  VoidTargetType,
} from "../lib/api/types";
import { apiPost } from "../lib/api/writeClient";

type WriteTab = "sale" | "expense" | "void" | "purchase" | "receivable" | "banking";
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
const BANK_TRANSFER_DEST_MSG =
  "Choose a different destination account for transfer.";

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

export function NewTransactionPage() {
  const salesOn = reactWriteSalesEnabled();
  const expensesOn = reactWriteExpensesEnabled();
  const voidsOn = reactWriteVoidsEnabled();
  const purchasesOn = reactWritePurchasesEnabled();
  const receivableOn = reactWriteReceivablePaymentsEnabled();
  const bankingOn = reactWriteBankingEnabled();
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

  if (!reactWriteEnabled()) {
    return (
      <section className="erp-placeholder">
        <h1>New Transaction</h1>
        <p>
          Write UI disabled. Set <code>VITE_ERP_REACT_WRITE_SALES=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_EXPENSES=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_PURCHASES=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS=1</code>,{" "}
          <code>VITE_ERP_REACT_WRITE_BANKING=1</code>, and/or{" "}
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
        setError("Enter a bank account id for card sales.");
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
        setError("Enter a bank account id for bank expenses.");
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
      setError("Enter a valid bank account id.");
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
            <label>
              Card bank account id
              <input
                type="number"
                min={1}
                value={cardBankAccountId}
                onChange={(event) => setCardBankAccountId(event.target.value)}
                required
              />
            </label>
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
            <label>
              Bank account id
              <input
                type="number"
                min={1}
                value={bankAccountId}
                onChange={(event) => setBankAccountId(event.target.value)}
                required
              />
            </label>
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
            <label>
              Bank account id
              <input
                type="number"
                min={1}
                value={purchaseBankAccountId}
                onChange={(event) => setPurchaseBankAccountId(event.target.value)}
                required
              />
            </label>
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
            <label>
              Bank account id
              <input
                type="number"
                min={1}
                value={receivableBankAccountId}
                onChange={(event) => setReceivableBankAccountId(event.target.value)}
                required
              />
            </label>
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
          <label>
            Bank account id
            <input
              type="number"
              min={1}
              value={bankingAccountId}
              onChange={(event) => setBankingAccountId(event.target.value)}
              required
            />
          </label>
          {bankTransactionType === "transfer" ? (
            <label>
              Destination bank account id
              <input
                type="number"
                min={1}
                value={bankingDestinationAccountId}
                onChange={(event) => setBankingDestinationAccountId(event.target.value)}
                required
              />
            </label>
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
    </section>
  );
}
