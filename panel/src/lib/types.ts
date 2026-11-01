export type Kpis = {
  revenue: number
  orders: number
  avg_ticket: number
  items_sold: number
  cogs: number
  gross_profit: number
}

export type LowStockItem = {
  item_code: string
  item_name: string
  stock_uom: string
  safety_stock: number
  actual_qty: number
}

export type RecentOrder = {
  name: string
  posting_date: string
  posting_time: string
  base_grand_total: number
  is_return: 0 | 1
  remarks: string | null
  owner: string
  owner_name: string
  customer_name: string | null
}

export type DashboardSummary = {
  range: { from: string; to: string }
  kpis: Kpis
  previous: Kpis
  trend: { date: string; revenue: number; orders: number }[]
  hourly: { hour: number; revenue: number; orders: number }[]
  top_items: { item_code: string; item_name: string; qty: number; revenue: number }[]
  by_group: { item_group: string; revenue: number; qty: number }[]
  group_items: Record<string, { item_code: string; item_name: string; qty: number; revenue: number }[]>
  payments: { mode_of_payment: string; amount: number; method_id?: number | null; account_name?: string | null }[]
  low_stock: LowStockItem[]
  recent_orders: RecentOrder[]
  source_payments?: SourcePaymentOverview
}

export type SourcePaymentOverview = {
  received: number
  outstanding: number
  credit_count: number
  unpaid_count: number
  partial_count: number
  unknown_count: number
  unallocated_count: number
  review_count?: number
  paid_count?: number
  cancelled_count?: number
  stale_debt_count?: number
}

export type CreditCustomer = {
  customer_id: number | null; customer_name: string | null
  credit: number; direct_received: number; known_outstanding: number
  account_balance: number | null; account_key: string | null; checked_at: string | null
  unallocated_count: number; unknown_count: number
  invoices: { name: string; posting_date: string; total: number; credit: number; received: number | null;
    outstanding: number | null; status: SourcePaymentSnapshot['status']; basis: SourcePaymentSnapshot['basis'] }[]
}

export type OrderTotals = {
  count: number; revenue: number; returns: number; source_payments?: SourcePaymentOverview
  credit_report?: { customers: CreditCustomer[]; account_debt: number; verified_accounts: number; unverified_customers: number }
  payment_methods?: { method_id?: number | null; mode_of_payment: string; amount: number; account_name?: string | null }[]
  direct_received?: number; account_settled?: number
  payment_catalog?: { method_id: number; name: string; account_name?: string | null }[]
}

export type PosItem = {
  item_code: string
  item_name: string
  item_group: string
  image: string | null
  description: string | null
  rate: number
}

export type PosMenu = { groups: string[]; items: PosItem[] }

export type Shift = {
  name: string
  user: string
  status: 'Open' | 'Closed'
  opening_time: string
  closing_time: string | null
  opening_cash: number
  closing_cash: number | null
  expected_cash: number
  cash_sales: number
  card_sales: number
  total_sales: number
  orders_count: number
  difference: number | null
  note?: string | null
}

export type MenuItem = {
  item_code: string
  item_name: string
  item_group: string
  image: string | null
  description: string | null
  disabled: 0 | 1
  has_recipe: boolean
  /** recipe rows that cannot be priced yet (no quantity or no purchase price) */
  unpriced?: number
  /** price, cost and margin are left out for a purchase manager — the server never sends them */
  rate?: number
  cost?: number
  margin?: number
}

/** A recipe row: a fixed cost per serving, or a quantity priced from the ingredient's purchase price. */
export type RecipeRow = {
  ingredient_name: string
  ingredient: string | null
  qty: number | null
  unit: string | null
  fixed_cost: number | null
  note?: string | null
  stock_uom?: string | null
  unit_price?: number
  cost?: number | null
}

export type MenuItemDetail = Omit<MenuItem, 'has_recipe' | 'cost' | 'margin' | 'unpriced'> & {
  recipe: RecipeRow[]
  recipe_notes: string | null
}

export type Ingredient = {
  item_code: string
  item_name: string
  item_group: string
  stock_uom: string
  safety_stock: number
  disabled: 0 | 1
  actual_qty: number
  valuation_rate: number
  stock_value: number
}

export type OrderRow = {
  name: string
  posting_date: string
  posting_time: string
  base_grand_total: number
  is_return: 0 | 1
  return_against: string | null
  status: string
  remarks: string | null
  owner: string
  owner_name: string
  payment_modes: string[]
  items_count: number
  source_payment?: SourcePaymentSnapshot
}

export type SourcePaymentSnapshot = {
  status: 'Unknown' | 'Unpaid' | 'Credit' | 'Partial' | 'Paid' | 'Cancelled'
  total: number | null
  received: number | null
  outstanding: number | null
  methods: { mode_of_payment: string; amount: number; method_id?: number | null; account_name?: string | null }[]
  checked_at: string | null
  is_stale?: boolean
  credit: number | null
  basis: 'Invoice' | 'Customer Account' | 'Unallocated'
  account_balance: number | null
  direct_received?: number | null
  source_factor?: number
  customer?: { id: number | null; name: string | null; account_key: string | null; account_verified: boolean }
  payment_catalog?: { method_id: number; name: string; account_name?: string | null }[]
  items?: { item_code: string; item_name: string; qty: number; rate: number; amount: number }[]
}

export type OrderDetail = {
  name: string
  posting_date: string
  posting_time: string
  status: string
  is_return: 0 | 1
  return_against: string | null
  remarks: string | null
  owner_name: string
  total: number
  discount_amount: number
  grand_total: number
  items: { item_code: string; item_name: string; qty: number; rate: number; amount: number }[]
  payments: { mode_of_payment: string; amount: number; method_id?: number | null; account_name?: string | null }[]
  has_return: boolean
  source_payment?: SourcePaymentSnapshot
  source_items_current?: boolean
  source_extra_amount?: number
  original_grand_total?: number
}

export type Movement = {
  posting_date: string
  posting_time: string
  item_code: string
  item_name: string
  stock_uom: string
  actual_qty: number
  qty_after_transaction: number
  stock_value_difference: number
  voucher_type: string
  voucher_no: string
}

export type Supplier = { name: string; supplier_name: string; mobile_no: string | null; total_purchases: number }

export type Purchase = {
  name: string
  supplier: string
  posting_date: string
  base_grand_total: number
  is_paid: 0 | 1
  outstanding_amount: number
  bill_no: string | null
}

export type AccountingOverview = {
  range: { from: string; to: string }
  income: number
  cogs: number
  gross_profit: number
  operating_expenses: number
  net_profit: number
  expenses_by_account: { account_name: string; account: string; amount: number }[]
  balances: { account: string; account_name: string; account_type: 'Cash' | 'Bank'; balance: number }[]
  monthly: { month: string; income: number; expense: number; profit: number }[]
}

export type ExpenseRow = {
  name: string
  posting_date: string
  user_remark: string | null
  account: string
  account_name: string
  amount: number
  owner: string
}

export type ContractState = 'active' | 'expiring' | 'expired' | 'upcoming' | 'open'

export type Contract = {
  name?: string
  position: string | null
  start_date: string | null
  end_date: string | null
  shift_start: string | null
  shift_end: string | null
  working_days: string | null
  monthly_salary: number
  payment_day: number | null
  sign_date: string | null
  note?: string | null
  state?: ContractState
  days_left?: number | null
}

export type Employee = {
  name?: string
  full_name: string
  national_id: string | null
  phone: string | null
  address: string | null
  birth_date: string | null
  status: 'Active' | 'Inactive'
  notes: string | null
  contracts: Contract[]
  current?: Contract[]
  monthly_salary?: number
}

export type BuyScope = 'Restaurant' | 'Cafe'
export type BuyPayment = 'Cash' | 'Card' | 'Transfer' | 'Credit'

export type BuyLine = {
  item_name: string
  ingredient: string | null
  qty: number | null
  unit: string | null
  unit_price: number
  amount: number
}

export type BuyPurchase = {
  name: string
  scope: BuyScope
  purchase_date: string
  supplier: string | null
  payment: BuyPayment
  total: number
  source: 'Manual' | 'Assistant'
  note: string | null
  owner: string
  owner_name: string
  creation: string
  items: BuyLine[]
}

export type BuyList = { rows: BuyPurchase[]; totals: Partial<Record<BuyScope, { total: number; count: number }>> }

export type ChequeDirection = 'Received' | 'Issued'
export type ChequeKind = 'Regular' | 'Guarantee' | 'Promissory'
export type ChequeStatus = 'Pending' | 'Cleared' | 'Bounced' | 'Transferred' | 'Returned' | 'Cancelled'

export type Cheque = {
  name?: string
  direction: ChequeDirection
  kind: ChequeKind
  party: string
  amount: number
  due_date: string | null
  status: ChequeStatus
  issue_date: string | null
  bank: string | null
  cheque_no: string | null
  sayad_id: string | null
  status_date?: string | null
  journal_entry?: string | null
  settled?: boolean
  note: string | null
}

export type ChequeSummary = { pending: number; pending_count: number; due_week: number; overdue: number; bounced: number }
export type ChequeList = { rows: Cheque[]; summary: Record<ChequeDirection, ChequeSummary> }

export type DayEvent = {
  type: 'contract' | 'payday' | 'birthday'
  title: string
  hint?: string | null
  amount?: number
  tone: 'info' | 'warn' | 'ok' | 'danger'
}

export type CalendarDay = {
  sales: { revenue: number; orders: number } | null
  purchases: { name: string; scope: BuyScope; desk: string; supplier: string | null; amount: number }[]
  expenses: { name: string; title: string; note: string | null; amount: number }[]
  cheques: Pick<Cheque, 'name' | 'direction' | 'kind' | 'party' | 'amount' | 'due_date' | 'status' | 'bank'>[]
  events: DayEvent[]
}

export type Alert = { tone: 'danger' | 'warn' | 'info' | 'ok'; title: string; text: string | null; link: string | null }
