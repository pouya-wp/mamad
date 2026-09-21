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
}

export type DashboardSummary = {
  range: { from: string; to: string }
  kpis: Kpis
  previous: Kpis
  trend: { date: string; revenue: number; orders: number }[]
  hourly: { hour: number; revenue: number; orders: number }[]
  top_items: { item_code: string; item_name: string; qty: number; revenue: number }[]
  by_group: { item_group: string; revenue: number; qty: number }[]
  payments: { mode_of_payment: string; amount: number }[]
  low_stock: LowStockItem[]
  recent_orders: RecentOrder[]
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
  rate: number
  has_recipe: boolean
  cost: number
  margin: number
}

export type RecipeRow = { item_code: string; item_name?: string; qty: number; uom?: string; rate?: number }

export type MenuItemDetail = Omit<MenuItem, 'has_recipe' | 'cost' | 'margin'> & { recipe: RecipeRow[] }

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
  payments: { mode_of_payment: string; amount: number }[]
  has_return: boolean
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
