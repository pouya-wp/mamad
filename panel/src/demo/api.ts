import { agentCall } from '@/demo/agent'
import { addOrder, type DemoOrder, hms, ordersBetween, ordersOfDay, RECIPES, world, ymd } from '@/demo/world'

/**
 * The backend, played by the browser. Every whitelisted method the panel calls
 * has an answer here, in the same shape ERPNext returns — and writes really do
 * change the demo's world, so a sale at the till moves the stock and the books.
 */

type Args = Record<string, any>

const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate())
const addDays = (date: Date, days: number) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)
const sum = <T>(rows: T[], get: (row: T) => number) => rows.reduce((total, row) => total + get(row), 0)

function periodRange(period = 'today', from?: string, to?: string) {
  const today = startOfDay(new Date())
  if (from && to) return { start: new Date(from), end: new Date(to) }
  const days = { today: 0, week: 6, month: 29, year: 364 }[period] ?? 0
  return { start: addDays(today, -days), end: today }
}

const inRange = (row: { date: Date }, start: Date, end: Date) => row.date >= start && row.date < addDays(end, 1)

function kpis(orders: DemoOrder[], until?: Date) {
  const rows = until ? orders.filter((o) => o.date.getHours() * 60 + o.date.getMinutes() <= until.getHours() * 60 + until.getMinutes()) : orders
  const revenue = sum(rows, (o) => o.grand_total)
  const cogs = sum(rows, (o) => o.cogs)
  const count = rows.filter((o) => !o.is_return).length
  return {
    revenue,
    orders: count,
    avg_ticket: count ? revenue / count : 0,
    items_sold: sum(rows, (o) => sum(o.items, (i) => i.qty)),
    cogs,
    gross_profit: revenue - cogs,
  }
}

const menuName = (code: string) => world.menu.find((m) => m.item_code === code)?.item_name ?? code
const ingredient = (code: string) => world.ingredients.find((i) => i.item_code === code)
const groupOf = (code: string) => world.menu.find((m) => m.item_code === code)?.item_group ?? 'سایر'

export function demoDispatch(method: string, args: Args = {}): unknown {
  const name = method.replace('cafe_app.api.', '')
  const today = startOfDay(new Date())

  switch (name) {
    // ---------------------------------------------------------------- session
    case 'session.boot':
      return {
        csrf_token: 'demo',
        user: { name: 'demo@one1cafe.ir', full_name: 'مدیر کافه', roles: ['Cafe Manager'], image: null },
        cafe: { company: 'ONE CAFE', currency: 'IRR', warehouse: 'انبار کافه', pos_profile: 'ONE CAFE', customer: 'مشتری کافه' },
      }

    // -------------------------------------------------------------- dashboard
    case 'dashboard.summary': {
      const { start, end } = periodRange(args.period, args.from_date, args.to_date)
      const length = Math.round((end.getTime() - start.getTime()) / 86400000) + 1
      const rows = ordersBetween(start, end)
      const prevRows = ordersBetween(addDays(start, -length), addDays(start, -1))
      const isToday = start.getTime() === end.getTime() && start.getTime() === today.getTime()

      const byItem = new Map<string, { qty: number; revenue: number }>()
      const byGroup = new Map<string, { qty: number; revenue: number }>()
      const byPayment = new Map<string, number>()
      const hourly = Array.from({ length: 24 }, (_, hour) => ({ hour, orders: 0, revenue: 0 }))
      for (const order of rows) {
        for (const line of order.items) {
          const item = byItem.get(line.item_code) ?? { qty: 0, revenue: 0 }
          item.qty += line.qty
          item.revenue += line.qty * line.rate
          byItem.set(line.item_code, item)
          const group = byGroup.get(groupOf(line.item_code)) ?? { qty: 0, revenue: 0 }
          group.qty += line.qty
          group.revenue += line.qty * line.rate
          byGroup.set(groupOf(line.item_code), group)
        }
        byPayment.set(order.mode, (byPayment.get(order.mode) ?? 0) + order.grand_total)
        hourly[order.date.getHours()].orders += 1
        hourly[order.date.getHours()].revenue += order.grand_total
      }

      const trend = Array.from({ length: 30 }, (_, i) => {
        const day = addDays(today, -(29 - i))
        const dayRows = ordersOfDay(day)
        return { date: ymd(day), revenue: sum(dayRows, (o) => o.grand_total), orders: dayRows.length }
      })

      return {
        range: { from: ymd(start), to: ymd(end) },
        kpis: kpis(rows),
        previous: kpis(prevRows, isToday ? new Date() : undefined),
        trend,
        hourly,
        top_items: [...byItem.entries()]
          .map(([item_code, value]) => ({ item_code, item_name: menuName(item_code), ...value }))
          .sort((a, b) => b.qty - a.qty)
          .slice(0, 8),
        by_group: [...byGroup.entries()]
          .map(([item_group, value]) => ({ item_group, ...value }))
          .sort((a, b) => b.revenue - a.revenue),
        payments: [...byPayment.entries()].map(([mode_of_payment, amount]) => ({ mode_of_payment, amount })).sort((a, b) => b.amount - a.amount),
        low_stock: demoDispatch('cafe_app.api.dashboard.low_stock'),
        recent_orders: [...world.orders]
          .slice(-8)
          .reverse()
          .map((o) => ({
            name: o.name,
            posting_date: ymd(o.date),
            posting_time: hms(o.date),
            base_grand_total: o.grand_total,
            is_return: o.is_return,
            remarks: `${o.type}${o.table ? ` | ${o.table}` : ''}`,
            owner: 'demo@one1cafe.ir',
          })),
      }
    }

    case 'dashboard.low_stock':
      return world.ingredients
        .filter((i) => world.stock[i.item_code] <= i.safety_stock)
        .map((i) => ({
          item_code: i.item_code,
          item_name: i.item_name,
          stock_uom: i.stock_uom,
          safety_stock: i.safety_stock,
          actual_qty: world.stock[i.item_code],
        }))
        .slice(0, 12)

    case 'dashboard.pulse': {
      const rows = ordersOfDay(today)
      const last = rows.at(-1)
      return {
        orders: rows.filter((o) => !o.is_return).length,
        revenue: sum(rows, (o) => o.grand_total),
        last: last ? { name: last.name, base_grand_total: last.grand_total, posting_time: hms(last.date), is_return: last.is_return } : null,
      }
    }

    // ------------------------------------------------------------------- menu
    case 'menu.get_groups':
      return world.groups

    case 'menu.list_menu':
      return world.menu.map((m) => {
        const cost = world.costOf(m.item_code)
        return {
          item_code: m.item_code,
          item_name: m.item_name,
          item_group: m.item_group,
          image: null,
          description: m.description ?? null,
          disabled: 0,
          rate: m.rate,
          has_recipe: cost > 0,
          cost,
          margin: m.rate ? ((m.rate - cost) / m.rate) * 100 : 0,
        }
      })

    case 'menu.get_menu_item': {
      const item = world.menu.find((m) => m.item_code === args.item_code)
      if (!item) throw new Error('آیتم پیدا نشد')
      return { ...item, image: null, description: item.description ?? null, disabled: 0, recipe: RECIPES[item.item_code] ?? [] }
    }

    case 'menu.save_menu_item': {
      const data = args.data as { item_code?: string; item_name: string; item_group: string; rate: number; description?: string }
      const existing = world.menu.find((m) => m.item_code === (data.item_code ?? data.item_name))
      if (existing) Object.assign(existing, { item_name: data.item_name, item_group: data.item_group, rate: data.rate, description: data.description ?? null })
      else world.menu.push({ item_code: data.item_name, item_name: data.item_name, item_group: data.item_group, rate: data.rate, description: data.description ?? null } as never)
      return data.item_name
    }

    case 'menu.list_ingredients':
      return world.ingredients.map((i) => ({
        ...i,
        disabled: 0,
        actual_qty: world.stock[i.item_code] ?? 0,
        stock_value: (world.stock[i.item_code] ?? 0) * i.valuation_rate,
      }))

    case 'menu.save_ingredient': {
      const data = args.data as { item_code?: string; item_name: string; item_group: string; stock_uom: string; safety_stock: number }
      const existing = world.ingredients.find((i) => i.item_code === (data.item_code ?? data.item_name))
      if (existing) Object.assign(existing, data)
      else {
        world.ingredients.push({ ...data, item_code: data.item_name, valuation_rate: 0, actual_qty: 0 } as never)
        world.stock[data.item_name] = 0
      }
      return data.item_name
    }

    // -------------------------------------------------------------- inventory
    case 'inventory.movements':
      return world.moves.slice(0, Number(args.limit ?? 40)).map((m) => ({
        posting_date: ymd(m.date),
        posting_time: hms(m.date),
        item_code: m.item_code,
        item_name: ingredient(m.item_code)?.item_name ?? m.item_code,
        stock_uom: ingredient(m.item_code)?.stock_uom ?? 'Nos',
        actual_qty: m.qty,
        qty_after_transaction: m.after,
        stock_value_difference: m.value,
        voucher_type: m.voucher_type,
        voucher_no: m.voucher_no,
      }))

    case 'inventory.record_waste': {
      const rows = (args.items ?? []) as { item_code: string; qty: number }[]
      const voucher = `MAT-STE-${world.serial++}`
      for (const row of rows) {
        world.stock[row.item_code] = (world.stock[row.item_code] ?? 0) - row.qty
        world.moves.unshift({
          date: new Date(),
          item_code: row.item_code,
          qty: -row.qty,
          after: world.stock[row.item_code],
          value: -row.qty * (ingredient(row.item_code)?.valuation_rate ?? 0),
          voucher_type: 'Stock Entry',
          voucher_no: voucher,
        })
      }
      return voucher
    }

    case 'inventory.stock_count': {
      const rows = (args.items ?? []) as { item_code: string; qty: number }[]
      const voucher = `MAT-RECO-${world.serial++}`
      for (const row of rows) {
        const before = world.stock[row.item_code] ?? 0
        world.stock[row.item_code] = row.qty
        world.moves.unshift({
          date: new Date(),
          item_code: row.item_code,
          qty: row.qty - before,
          after: row.qty,
          value: (row.qty - before) * (ingredient(row.item_code)?.valuation_rate ?? 0),
          voucher_type: 'Stock Reconciliation',
          voucher_no: voucher,
        })
      }
      return voucher
    }

    case 'inventory.list_purchases':
      return [...world.purchases]
        .reverse()
        .slice(0, 40)
        .map((p) => ({
          name: p.name,
          supplier: p.supplier,
          posting_date: ymd(p.date),
          base_grand_total: p.total,
          is_paid: p.is_paid,
          outstanding_amount: p.is_paid ? 0 : p.total,
          bill_no: p.bill_no,
        }))

    case 'inventory.list_suppliers':
      return world.suppliers.map((s) => ({
        ...s,
        total_purchases: sum(
          world.purchases.filter((p) => p.supplier === s.name),
          (p) => p.total,
        ),
      }))

    case 'inventory.record_purchase': {
      const items = (args.items ?? []) as { item_code: string; qty: number; rate: number }[]
      const purchase = {
        name: `ACC-PINV-${today.getFullYear()}-${String(world.purchases.length + 1).padStart(5, '0')}`,
        supplier: String(args.supplier),
        date: new Date(),
        items,
        total: sum(items, (i) => i.qty * i.rate),
        is_paid: (args.mode_of_payment ? 1 : 0) as 0 | 1,
        bill_no: (args.bill_no as string) ?? null,
      }
      world.purchases.push(purchase)
      for (const line of items) {
        world.stock[line.item_code] = (world.stock[line.item_code] ?? 0) + line.qty
        world.moves.unshift({
          date: purchase.date,
          item_code: line.item_code,
          qty: line.qty,
          after: world.stock[line.item_code],
          value: line.qty * line.rate,
          voucher_type: 'Purchase Invoice',
          voucher_no: purchase.name,
        })
      }
      return purchase.name
    }

    case 'inventory.save_supplier': {
      const supplier = { name: String(args.supplier_name), supplier_name: String(args.supplier_name), mobile_no: (args.mobile_no as string) ?? null }
      world.suppliers.push(supplier as never)
      return supplier.name
    }

    // ----------------------------------------------------------------- orders
    case 'orders.list_orders': {
      const start = args.from_date ? new Date(String(args.from_date)) : null
      const end = args.to_date ? new Date(String(args.to_date)) : null
      const search = String(args.search ?? '').trim()
      let rows = start && end ? [...ordersBetween(start, end)].reverse() : [...world.orders].reverse()
      if (search) rows = rows.filter((o) => o.name.includes(search) || o.items.some((i) => i.item_code.includes(search)))
      return rows.slice(Number(args.start ?? 0), Number(args.start ?? 0) + Number(args.limit ?? 40)).map(orderRow)
    }

    case 'orders.get_order': {
      const order = world.orders.find((o) => o.name === args.name)
      if (!order) throw new Error('سفارش پیدا نشد')
      return {
        name: order.name,
        posting_date: ymd(order.date),
        posting_time: hms(order.date),
        status: order.is_return ? 'Return' : 'Paid',
        is_return: order.is_return,
        return_against: order.return_against,
        remarks: `${order.type}${order.table ? ` | ${order.table}` : ''}`,
        owner_name: 'صندوق‌دار کافه',
        total: order.total,
        discount_amount: order.discount,
        grand_total: order.grand_total,
        items: order.items.map((line) => ({
          item_code: line.item_code,
          item_name: menuName(line.item_code),
          qty: line.qty,
          rate: line.rate,
          amount: line.qty * line.rate,
        })),
        payments: [{ mode_of_payment: order.mode, amount: order.grand_total }],
        has_return: order.returned,
      }
    }

    case 'orders.return_order': {
      const order = world.orders.find((o) => o.name === args.name)
      if (!order) throw new Error('سفارش پیدا نشد')
      if (order.returned) throw new Error('این سفارش قبلاً مرجوع شده')
      order.returned = true
      const credit: DemoOrder = {
        ...order,
        name: `${order.name}-R`,
        date: new Date(),
        items: order.items.map((line) => ({ ...line, qty: -line.qty })),
        total: -order.total,
        discount: -order.discount,
        grand_total: -order.grand_total,
        cogs: -order.cogs,
        is_return: 1,
        return_against: order.name,
        returned: false,
      }
      addOrder(credit)
      return credit.name
    }

    // -------------------------------------------------------------------- POS
    case 'pos.get_menu':
      return {
        groups: world.groups.menu,
        items: world.menu.map((m) => ({
          item_code: m.item_code,
          item_name: m.item_name,
          item_group: m.item_group,
          image: null,
          description: m.description ?? null,
          rate: m.rate,
        })),
      }

    case 'pos.current_shift': {
      const open = world.shifts.find((s) => !s.closing)
      return open ? shiftRow(open) : null
    }

    case 'pos.open_shift': {
      const now = new Date()
      const shift = {
        name: `SHIFT-${ymd(now)}-${world.serial++}`,
        date: startOfDay(now),
        opening: now,
        closing: null,
        opening_cash: Number(args.opening_cash ?? 0),
        closing_cash: null,
        note: null,
      }
      world.shifts.push(shift)
      return shiftRow(shift)
    }

    case 'pos.close_shift': {
      const open = world.shifts.find((s) => !s.closing)
      if (!open) throw new Error('شیفت بازی نیست')
      open.closing = new Date()
      open.closing_cash = Number(args.closing_cash ?? 0)
      open.note = (args.note as string) ?? null
      return shiftRow(open)
    }

    case 'pos.list_shifts':
      return [...world.shifts].reverse().slice(0, Number(args.limit ?? 60)).map(shiftRow)

    case 'pos.create_order': {
      const lines = (args.items ?? []) as { item_code: string; qty: number }[]
      const items = lines.map((line) => ({ ...line, rate: world.menu.find((m) => m.item_code === line.item_code)?.rate ?? 0 }))
      const total = sum(items, (i) => i.qty * i.rate)
      const discount = Number(args.discount_amount ?? 0)
      const payments = (args.payments ?? []) as { mode_of_payment: string; amount: number }[]
      const order: DemoOrder = {
        name: `ACC-SINV-${today.getFullYear()}-${String(world.serial++).padStart(5, '0')}`,
        date: new Date(),
        day: ymd(new Date()),
        items,
        total,
        discount,
        grand_total: total - discount,
        cogs: sum(items, (i) => i.qty * world.costOf(i.item_code)),
        mode: payments[0]?.mode_of_payment ?? 'نقدی',
        type: String(args.order_type ?? 'سالن'),
        table: (args.table_no as string) ?? null,
        is_return: 0,
        return_against: null,
        returned: false,
      }
      addOrder(order)
      sell(order)
      return { name: order.name, grand_total: order.grand_total }
    }

    // ------------------------------------------------------------- accounting
    case 'accounting.overview': {
      const { start, end } = periodRange(args.period, args.from_date, args.to_date)
      const orders = ordersBetween(start, end)
      const expenses = world.expenses.filter((e) => inRange(e, start, end))
      const income = sum(orders, (o) => o.grand_total)
      const cogs = sum(orders, (o) => o.cogs)
      const operating = sum(expenses, (e) => e.amount)

      const byAccount = new Map<string, number>()
      for (const expense of expenses) byAccount.set(expense.account, (byAccount.get(expense.account) ?? 0) + expense.amount)

      const monthly = Array.from({ length: 6 }, (_, i) => {
        const month = new Date(today.getFullYear(), today.getMonth() - (5 - i), 1)
        const next = new Date(month.getFullYear(), month.getMonth() + 1, 1)
        const rows = ordersBetween(month, addDays(next, -1))
        const spent = world.expenses.filter((e) => e.date >= month && e.date < next)
        const monthIncome = sum(rows, (o) => o.grand_total)
        const monthExpense = sum(rows, (o) => o.cogs) + sum(spent, (e) => e.amount)
        return { month: ymd(month), income: monthIncome, expense: monthExpense, profit: monthIncome - monthExpense }
      })

      const cashIn = sum(
        orders.filter((o) => o.mode === 'نقدی'),
        (o) => o.grand_total,
      )
      const cardIn = sum(
        orders.filter((o) => o.mode === 'کارتخوان'),
        (o) => o.grand_total,
      )

      return {
        range: { from: ymd(start), to: ymd(end) },
        income,
        cogs,
        gross_profit: income - cogs,
        operating_expenses: operating,
        net_profit: income - cogs - operating,
        expenses_by_account: [...byAccount.entries()]
          .map(([account, amount]) => ({ account, account_name: account.replace(' - CO', ''), amount }))
          .sort((a, b) => b.amount - a.amount),
        balances: [
          { account: 'صندوق - CO', account_name: 'صندوق', account_type: 'Cash' as const, balance: cashIn * 0.2 },
          { account: 'بانک - CO', account_name: 'حساب بانکی', account_type: 'Bank' as const, balance: cardIn * 0.35 },
        ],
        monthly,
      }
    }

    case 'accounting.list_expenses':
      return [...world.expenses]
        .reverse()
        .slice(0, Number(args.limit ?? 20))
        .map((e) => ({
          name: e.name,
          posting_date: ymd(e.date),
          user_remark: e.note,
          account: e.account,
          account_name: e.account.replace(' - CO', ''),
          amount: e.amount,
          owner: 'demo@one1cafe.ir',
        }))

    case 'accounting.expense_accounts':
      return world.accounts

    case 'accounting.record_expense': {
      const expense = {
        name: `ACC-JV-${today.getFullYear()}-${String(world.expenses.length + 1).padStart(5, '0')}`,
        date: args.posting_date ? new Date(String(args.posting_date)) : new Date(),
        account: String(args.account),
        amount: Number(args.amount ?? 0),
        note: (args.note as string) ?? null,
        mode: String(args.mode_of_payment ?? 'نقدی'),
      }
      world.expenses.push(expense)
      return expense.name
    }

    // ------------------------------------------------------------------ agent
    default:
      return agentCall(name, args)
  }
}

function orderRow(order: DemoOrder) {
  return {
    name: order.name,
    posting_date: ymd(order.date),
    posting_time: hms(order.date),
    base_grand_total: order.grand_total,
    is_return: order.is_return,
    return_against: order.return_against,
    status: order.is_return ? 'Return' : 'Paid',
    remarks: `${order.type}${order.table ? ` | ${order.table}` : ''}`,
    owner: 'demo@one1cafe.ir',
    owner_name: 'صندوق‌دار کافه',
    payment_modes: [order.mode],
    items_count: order.items.length,
  }
}

function shiftRow(shift: (typeof world.shifts)[number]) {
  const rows = ordersOfDay(shift.date).filter((o) => o.date >= shift.opening && (!shift.closing || o.date <= shift.closing))
  const cash = sum(
    rows.filter((o) => o.mode === 'نقدی'),
    (o) => o.grand_total,
  )
  const card = sum(
    rows.filter((o) => o.mode === 'کارتخوان'),
    (o) => o.grand_total,
  )
  const expected = shift.opening_cash + cash
  return {
    name: shift.name,
    user: 'صندوق‌دار کافه',
    status: (shift.closing ? 'Closed' : 'Open') as 'Open' | 'Closed',
    opening_time: `${ymd(shift.opening)} ${hms(shift.opening)}`,
    closing_time: shift.closing ? `${ymd(shift.closing)} ${hms(shift.closing)}` : null,
    opening_cash: shift.opening_cash,
    closing_cash: shift.closing_cash,
    expected_cash: expected,
    cash_sales: cash,
    card_sales: card,
    total_sales: cash + card,
    orders_count: rows.length,
    difference: shift.closing_cash === null ? null : shift.closing_cash - expected,
    note: shift.note,
  }
}

/** A sale takes its recipe out of the store room. */
export function sell(order: DemoOrder) {
  for (const line of order.items) {
    for (const row of RECIPES[line.item_code] ?? []) {
      const used = row.qty * line.qty
      world.stock[row.item_code] = (world.stock[row.item_code] ?? 0) - used
      world.moves.unshift({
        date: order.date,
        item_code: row.item_code,
        qty: -used,
        after: world.stock[row.item_code],
        value: -used * row.rate,
        voucher_type: 'Sales Invoice',
        voucher_no: order.name,
      })
    }
  }
}
