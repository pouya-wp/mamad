import { hms, world, ymd } from '@/demo/world'

/**
 * The assistant, offline. Same contract as the backend's agent API — Persian
 * intents in, text plus printable blocks out — so the demo answers real questions
 * about the demo café and can even post to its books, once you stamp the slip.
 */

type Args = Record<string, any>
type Block = Record<string, unknown>

const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate())
const addDays = (date: Date, days: number) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)
const sum = <T>(rows: T[], get: (row: T) => number) => rows.reduce((total, row) => total + get(row), 0)
const toman = (rial: number) => Math.round(rial / 10).toLocaleString('fa-IR')
const fa = (value: number) => value.toLocaleString('fa-IR')

const DIGITS: Record<string, string> = { '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9' }
const normalize = (text: string) =>
  text
    .replace(/[۰-۹]/g, (d) => DIGITS[d])
    .replace(/‌/g, ' ')
    .replace(/ي/g, 'ی')
    .replace(/ك/g, 'ک')
    .toLowerCase()

/** "۸ میلیون" or "۳۵۰ هزار تومان" → the amount in rial. */
function parseAmount(text: string): number | null {
  const clean = normalize(text)
  const match = clean.match(/(\d[\d.,]*)\s*(میلیون|میلیارد|هزار)?/)
  if (!match) return null
  const base = Number(match[1].replace(/[.,]/g, ''))
  if (!base) return null
  const scale = match[2] === 'میلیارد' ? 1_000_000_000 : match[2] === 'میلیون' ? 1_000_000 : match[2] === 'هزار' ? 1_000 : 1
  return base * scale * 10 // toman → rial
}

function ordersBetween(start: Date, end: Date) {
  return world.orders.filter((o) => o.date >= start && o.date < addDays(end, 1))
}

function range(text: string) {
  const today = startOfDay(new Date())
  if (/دیروز/.test(text)) return { label: 'دیروز', start: addDays(today, -1), end: addDays(today, -1) }
  if (/هفته/.test(text)) return { label: 'این هفته', start: addDays(today, -6), end: today }
  if (/ماه/.test(text)) return { label: 'این ماه', start: addDays(today, -29), end: today }
  return { label: 'امروز', start: today, end: today }
}

// ---------------------------------------------------------------- proposals

type Proposal = { id: string; kind: 'expense' | 'purchase' | 'waste'; payload: Args; title: string }
const proposals = new Map<string, Proposal>()

function proposalBlock(proposal: Proposal, lines: { label: string; value: number | string; format?: string; uom?: string }[]): Block {
  return { type: 'proposal', id: proposal.id, title: proposal.title, lines, status: 'pending' }
}

function newProposal(kind: Proposal['kind'], title: string, payload: Args) {
  const proposal: Proposal = { id: `demo-${Math.random().toString(36).slice(2, 10)}`, kind, title, payload }
  proposals.set(proposal.id, proposal)
  return proposal
}

/** Stamping a slip really writes to the demo's books. */
function apply(proposal: Proposal) {
  const now = new Date()
  if (proposal.kind === 'expense') {
    const name = `ACC-JV-${now.getFullYear()}-${String(world.expenses.length + 1).padStart(5, '0')}`
    world.expenses.push({
      name,
      date: now,
      account: proposal.payload.account,
      amount: proposal.payload.amount,
      note: proposal.payload.note ?? null,
      mode: proposal.payload.mode ?? 'نقدی',
    })
    return { message: 'هزینه ثبت شد', document: name }
  }

  if (proposal.kind === 'purchase') {
    const name = `ACC-PINV-${now.getFullYear()}-${String(world.purchases.length + 1).padStart(5, '0')}`
    const item = proposal.payload.item_code as string
    const qty = proposal.payload.qty as number
    const rate = proposal.payload.rate as number
    world.purchases.push({ name, supplier: proposal.payload.supplier, date: now, items: [{ item_code: item, qty, rate }], total: qty * rate, is_paid: 1, bill_no: null })
    world.stock[item] = (world.stock[item] ?? 0) + qty
    world.moves.unshift({ date: now, item_code: item, qty, after: world.stock[item], value: qty * rate, voucher_type: 'Purchase Invoice', voucher_no: name })
    return { message: 'خرید ثبت شد و موجودی بالا رفت', document: name }
  }

  const name = `MAT-STE-${world.serial++}`
  const item = proposal.payload.item_code as string
  const qty = proposal.payload.qty as number
  world.stock[item] = (world.stock[item] ?? 0) - qty
  world.moves.unshift({
    date: now,
    item_code: item,
    qty: -qty,
    after: world.stock[item],
    value: -qty * (world.ingredients.find((i) => i.item_code === item)?.valuation_rate ?? 0),
    voucher_type: 'Stock Entry',
    voucher_no: name,
  })
  return { message: 'ضایعات ثبت شد', document: name }
}

// ------------------------------------------------------------------ answers

const SUGGESTIONS = [
  'فروش امروز چطور بود؟',
  'سود و زیان این ماه',
  'چی داره تموم میشه؟',
  'پرفروش‌های این هفته',
  '۱۲ میلیون حقوق باریستا دادم',
  '۵ کیلو شیر خریدم ۳۰۰ هزار تومن',
]

function salesAnswer(text: string) {
  const { label, start, end } = range(text)
  const rows = ordersBetween(start, end)
  const revenue = sum(rows, (o) => o.grand_total)
  const count = rows.filter((o) => !o.is_return).length
  const cogs = sum(rows, (o) => o.cogs)
  const length = Math.round((end.getTime() - start.getTime()) / 86400000) + 1
  const before = ordersBetween(addDays(start, -length), addDays(start, -1))
  const beforeRevenue = sum(before, (o) => o.grand_total)
  const change = beforeRevenue ? ((revenue - beforeRevenue) / beforeRevenue) * 100 : null

  return {
    text: `${label} ${fa(count)} سفارش زدی و ${toman(revenue)} تومان فروختی. سود ناخالصش ${toman(revenue - cogs)} تومان می‌شود${
      change === null ? '' : `، ${change >= 0 ? 'بالاتر' : 'پایین‌تر'} از دوره قبل`
    }.`,
    blocks: [
      {
        type: 'metrics',
        title: `فروش ${label}`,
        items: [
          { label: 'فروش', value: revenue, format: 'toman', change },
          { label: 'سفارش‌ها', value: count, format: 'number' },
          { label: 'میانگین هر فاکتور', value: count ? revenue / count : 0, format: 'toman' },
          { label: 'سود ناخالص', value: revenue - cogs, format: 'toman' },
        ],
      },
    ],
    suggestions: ['پرفروش‌های امروز', 'سود و زیان این ماه'],
  }
}

function profitAnswer(text: string) {
  const { label, start, end } = range(/امروز|دیروز|هفته/.test(text) ? text : 'ماه')
  const rows = ordersBetween(start, end)
  const spent = world.expenses.filter((e) => e.date >= start && e.date < addDays(end, 1))
  const income = sum(rows, (o) => o.grand_total)
  const cogs = sum(rows, (o) => o.cogs)
  const operating = sum(spent, (e) => e.amount)
  const net = income - cogs - operating
  const biggest = [...spent].sort((a, b) => b.amount - a.amount)[0]

  return {
    text: `${label} ${toman(income)} تومان درآمد داشتی و ${toman(cogs + operating)} تومان خرج. سود خالص ${toman(net)} تومان است${
      biggest ? `؛ بزرگ‌ترین هزینه‌ات ${biggest.account.replace(' - CO', '')} بوده با ${toman(biggest.amount)} تومان` : ''
    }.`,
    blocks: [
      {
        type: 'metrics',
        title: `سود و زیان ${label}`,
        items: [
          { label: 'درآمد', value: income, format: 'toman' },
          { label: 'بهای تمام‌شده', value: cogs, format: 'toman' },
          { label: 'هزینه‌های جاری', value: operating, format: 'toman' },
          { label: 'سود خالص', value: net, format: 'toman' },
        ],
      },
    ],
    suggestions: ['هزینه‌های این ماه', 'فروش این هفته'],
  }
}

function stockAnswer() {
  const low = world.ingredients
    .filter((i) => world.stock[i.item_code] <= i.safety_stock)
    .sort((a, b) => world.stock[a.item_code] / (a.safety_stock || 1) - world.stock[b.item_code] / (b.safety_stock || 1))
  if (!low.length) {
    return { text: 'همه‌چیز بالای حد مجاز است؛ فعلاً لازم نیست سفارش بدهی.', blocks: [], suggestions: ['ارزش موجودی انبار', 'خرید این هفته'] }
  }
  return {
    text: `${fa(low.length)} قلم زیر حد مجاز است. اگر امروز سفارش بدهی، فردا بی‌دردسر باز می‌کنی.`,
    blocks: [
      {
        type: 'list',
        title: 'اقلام رو به اتمام',
        items: low.slice(0, 8).map((i) => ({
          label: i.item_name,
          value: world.stock[i.item_code],
          format: 'number',
          uom: i.stock_uom,
          hint: `حد مجاز ${fa(i.safety_stock)}`,
          tone: world.stock[i.item_code] <= 0 ? 'danger' : 'warn',
        })),
      },
    ],
    suggestions: ['۵ کیلو شیر خریدم ۳۰۰ هزار تومن', 'ارزش موجودی انبار'],
  }
}

function topAnswer(text: string) {
  const { label, start, end } = range(text)
  const rows = ordersBetween(start, end)
  const byItem = new Map<string, number>()
  for (const order of rows) for (const line of order.items) byItem.set(line.item_code, (byItem.get(line.item_code) ?? 0) + line.qty)
  const top = [...byItem.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6)
  if (!top.length) return { text: 'هنوز فروشی برای این بازه ثبت نشده.', blocks: [], suggestions: SUGGESTIONS.slice(0, 3) }
  return {
    text: `پرفروش‌ترین ${label} ${top[0][0]} بوده با ${fa(top[0][1])} فروش.`,
    blocks: [{ type: 'list', title: `پرفروش‌های ${label}`, items: top.map(([code, qty]) => ({ label: code, value: qty, format: 'number' })) }],
    suggestions: ['سود و زیان این ماه', 'چی داره تموم میشه؟'],
  }
}

function expensesAnswer() {
  const today = startOfDay(new Date())
  const start = addDays(today, -29)
  const rows = world.expenses.filter((e) => e.date >= start)
  const byAccount = new Map<string, number>()
  for (const expense of rows) byAccount.set(expense.account, (byAccount.get(expense.account) ?? 0) + expense.amount)
  const items = [...byAccount.entries()].sort((a, b) => b[1] - a[1])
  return {
    text: `در ۳۰ روز گذشته ${toman(sum(rows, (e) => e.amount))} تومان هزینه ثبت شده.`,
    blocks: [
      {
        type: 'list',
        title: 'هزینه‌های ۳۰ روز اخیر',
        items: items.map(([account, amount]) => ({ label: account.replace(' - CO', ''), value: amount, format: 'toman' })),
      },
    ],
    suggestions: ['سود و زیان این ماه', '۸ میلیون قبض برق دادم'],
  }
}

function cashAnswer() {
  const today = startOfDay(new Date())
  const rows = ordersBetween(today, today)
  const cash = sum(
    rows.filter((o) => o.mode === 'نقدی'),
    (o) => o.grand_total,
  )
  const card = sum(
    rows.filter((o) => o.mode === 'کارتخوان'),
    (o) => o.grand_total,
  )
  return {
    text: `امروز ${toman(cash)} تومان نقدی و ${toman(card)} تومان کارتخوان داشتی.`,
    blocks: [
      {
        type: 'metrics',
        title: 'صندوق امروز',
        items: [
          { label: 'نقدی', value: cash, format: 'toman' },
          { label: 'کارتخوان', value: card, format: 'toman' },
        ],
      },
    ],
    suggestions: ['فروش امروز چطور بود؟', 'سود و زیان این ماه'],
  }
}

/** "۸ میلیون قبض برق دادم" → a slip that posts an expense. */
function expenseProposal(text: string) {
  const amount = parseAmount(text)
  if (!amount) return null
  const clean = normalize(text)
  const account =
    /برق|آب|گاز|قبض/.test(clean) ? 'آب، برق و گاز - CO'
    : /حقوق|دستمزد|باریستا|پرسنل/.test(clean) ? 'حقوق و دستمزد - CO'
    : /اجاره|رهن|مالک/.test(clean) ? 'اجاره - CO'
    : /اینترنت|تلفن|شارژ/.test(clean) ? 'اینترنت و تلفن - CO'
    : /تبلیغ|اینستا|بازاریابی/.test(clean) ? 'تبلیغات و بازاریابی - CO'
    : /تعمیر|سرویس|خراب/.test(clean) ? 'تعمیرات و نگهداری - CO'
    : /شوینده|ملزومات|دستمال/.test(clean) ? 'ملزومات و شوینده - CO'
    : 'سایر هزینه‌ها - CO'

  const proposal = newProposal('expense', 'ثبت هزینه', { account, amount, note: text, mode: /کارت|پوز|دستگاه/.test(clean) ? 'کارتخوان' : 'نقدی' })
  return {
    text: 'این هزینه رو برات آماده کردم. نگاه بنداز و تأیید کن تا توی حسابداری ثبت بشه 👇',
    blocks: [
      proposalBlock(proposal, [
        { label: 'نوع هزینه', value: account.replace(' - CO', '') },
        { label: 'مبلغ', value: amount, format: 'toman' },
        { label: 'پرداخت از', value: proposal.payload.mode },
        { label: 'تاریخ', value: ymd(new Date()), format: 'date' },
      ]),
    ],
    suggestions: ['هزینه‌های این ماه', 'سود و زیان این ماه'],
  }
}

/** "۵ کیلو شیر خریدم ۳۰۰ هزار" → a purchase slip that also moves the stock. */
function purchaseProposal(text: string) {
  const clean = normalize(text)
  const item = world.ingredients.find((i) => clean.includes(normalize(i.item_name)))
  if (!item) return null
  const [first, second] = clean.match(/\d[\d.,]*\s*(میلیون|هزار)?/g) ?? []
  if (!first) return null
  const qty = Number(first.replace(/[^\d]/g, '')) || 1
  const price = second ? parseAmount(second) : null
  const rate = price ? price / qty : item.valuation_rate
  const supplier = world.suppliers[0]?.name ?? 'تأمین‌کننده'

  const proposal = newProposal('purchase', 'ثبت خرید', { item_code: item.item_code, qty, rate, supplier })
  return {
    text: 'فیش خرید آماده است؛ با تأیید تو هم انبار پر می‌شود هم دفتر خرید.',
    blocks: [
      proposalBlock(proposal, [
        { label: 'قلم', value: item.item_name },
        { label: 'مقدار', value: qty, format: 'number', uom: item.stock_uom },
        { label: 'قیمت واحد', value: rate, format: 'toman' },
        { label: 'جمع', value: qty * rate, format: 'toman' },
        { label: 'تأمین‌کننده', value: supplier },
      ]),
    ],
    suggestions: ['چی داره تموم میشه؟', 'خرید این هفته'],
  }
}

/** "۲ لیتر شیر ریخت" → a waste slip. */
function wasteProposal(text: string) {
  const clean = normalize(text)
  const item = world.ingredients.find((i) => clean.includes(normalize(i.item_name)))
  if (!item) return null
  const qty = Number((clean.match(/\d+/) ?? ['1'])[0])
  const proposal = newProposal('waste', 'ثبت ضایعات', { item_code: item.item_code, qty })
  return {
    text: 'ضایعات را آماده کردم؛ با تأیید از موجودی کم می‌شود.',
    blocks: [
      proposalBlock(proposal, [
        { label: 'قلم', value: item.item_name },
        { label: 'مقدار', value: qty, format: 'number', uom: item.stock_uom },
        { label: 'دلیل', value: 'ضایعات' },
      ]),
    ],
    suggestions: ['چی داره تموم میشه؟', 'ارزش موجودی انبار'],
  }
}

function answer(message: string) {
  const text = normalize(message)

  if (/ضایعات|ریخت|خراب شد|دور ریخت/.test(text)) {
    const waste = wasteProposal(message)
    if (waste) return waste
  }
  if (/خرید|گرفتم|سفارش دادم/.test(text)) {
    const purchase = purchaseProposal(message)
    if (purchase) return purchase
  }
  if (/دادم|پرداخت|قبض|حقوق|اجاره|هزینه کردم/.test(text)) {
    const expense = expenseProposal(message)
    if (expense) return expense
  }
  if (/سود|زیان|ضرر|حاشیه/.test(text)) return profitAnswer(text)
  if (/پرفروش|محبوب|بیشترین فروش/.test(text)) return topAnswer(text)
  if (/نقد|کارتخوان|صندوق/.test(text)) return cashAnswer()
  if (/موجودی|انبار|تموم|کم داریم|سفارش بدم/.test(text)) return stockAnswer()
  if (/هزینه|خرج/.test(text)) return expensesAnswer()
  if (/فروش|درآمد|امروز|دیروز|هفته|ماه/.test(text)) return salesAnswer(text)
  if (/سلام|خوبی|چه خبر|هستی/.test(text)) {
    return {
      text: 'سلام! من دستیار One هستم، حساب‌وکتاب کافه با من: می‌توانی وضع فروش و سود را بپرسی، یا فقط بگویی چه پولی دادی و چه خریدی تا برایت ثبتش کنم.',
      blocks: [],
      suggestions: SUGGESTIONS.slice(0, 4),
    }
  }

  return {
    text: 'این را نفهمیدم. می‌توانی درباره فروش، سود، موجودی و هزینه‌ها بپرسی، یا خرید و هزینه‌ای که انجام دادی را بگویی تا ثبتش کنم.',
    blocks: [],
    suggestions: SUGGESTIONS.slice(0, 4),
  }
}

export function agentCall(name: string, args: Args) {
  switch (name) {
    case 'agent.status':
      return { mode: 'demo', suggestions: SUGGESTIONS }

    case 'agent.chat':
      return { ...answer(String(args.message ?? '')), mode: 'demo' }

    case 'agent.confirm': {
      const proposal = proposals.get(String(args.proposal_id))
      if (!proposal) throw new Error('این پیشنهاد دیگر معتبر نیست')
      proposals.delete(proposal.id)
      return apply(proposal)
    }

    case 'agent.cancel':
      proposals.delete(String(args.proposal_id))
      return true

    case 'agent.insights': {
      const today = startOfDay(new Date())
      const todayRows = ordersBetween(today, today)
      const yesterday = ordersBetween(addDays(today, -1), addDays(today, -1)).filter(
        (o) => o.date.getHours() * 60 + o.date.getMinutes() <= new Date().getHours() * 60 + new Date().getMinutes(),
      )
      const revenue = sum(todayRows, (o) => o.grand_total)
      const before = sum(yesterday, (o) => o.grand_total)
      const change = before ? ((revenue - before) / before) * 100 : 0
      const low = world.ingredients.filter((i) => world.stock[i.item_code] <= i.safety_stock)

      const month = ordersBetween(addDays(today, -29), today)
      const spent = world.expenses.filter((e) => e.date >= addDays(today, -29))
      const net = sum(month, (o) => o.grand_total) - sum(month, (o) => o.cogs) - sum(spent, (e) => e.amount)
      const margin = sum(month, (o) => o.grand_total) ? (net / sum(month, (o) => o.grand_total)) * 100 : 0

      const hours = new Map<number, number>()
      for (const order of ordersBetween(addDays(today, -6), today)) hours.set(order.date.getHours(), (hours.get(order.date.getHours()) ?? 0) + 1)
      const peak = [...hours.entries()].sort((a, b) => b[1] - a[1])[0]

      const insights = [
        {
          tone: change >= 0 ? 'up' : 'down',
          text: `فروش امروز تا الان ${toman(revenue)} تومان است، ${fa(Math.abs(Math.round(change)))}٪ ${change >= 0 ? 'بیشتر' : 'کمتر'} از همین ساعت دیروز.`,
          ask: 'فروش امروز چطور بود؟',
        },
        low.length
          ? { tone: 'warn', text: `${fa(low.length)} قلم رو به اتمام است (${low.slice(0, 3).map((i) => i.item_name).join('، ')}). بهتره امروز سفارش بدی.`, ask: 'چی داره تموم میشه؟' }
          : { tone: 'info', text: 'موجودی همه اقلام بالای حد مجاز است.', ask: 'ارزش موجودی انبار' },
        { tone: net >= 0 ? 'up' : 'down', text: `حاشیه سود خالص ۳۰ روز اخیر ${fa(Math.round(margin))}٪ بوده (${toman(net)} تومان).`, ask: 'سود و زیان این ماه' },
        peak
          ? { tone: 'info', text: `شلوغ‌ترین ساعت هفته ${fa(peak[0])} تا ${fa(peak[0] + 1)} بوده؛ برای این ساعت نیروی بیشتری بذار.`, ask: 'پرفروش‌های این هفته' }
          : { tone: 'info', text: 'هنوز داده کافی برای الگوی ساعتی نیست.', ask: 'فروش این هفته' },
      ]
      return insights
    }

    default:
      throw new Error(`متد ${name} در نسخه نمایشی پیاده نشده`)
  }
}

export const demoNow = () => `${ymd(new Date())} ${hms(new Date())}`
