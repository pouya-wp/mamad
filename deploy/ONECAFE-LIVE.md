# One Cafe temporary VPS deployment

Deployed on 2026-09-26 at `https://onecafe.beyondex.one` (`95.38.191.245`).

## 2026-10-21: buyer expenses, staff advances, and manager activity

- Both purchase manager accounts have an `Expenses` page for restaurant and
  café entries. A regular expense posts a balanced Journal Entry to an eligible
  expense account. An employee advance posts to the dedicated current-asset
  account `مساعده کارکنان`, so it does not reduce current profit. Both payment
  methods use the existing cash or card account mapping; only active café
  employees can receive advances. Expense and advance entries are immutable in
  the buyer panel after posting and retain their Journal Entry link.
- The manager's last sidebar section is `فعالیت مسئولان خرید`. It records buyer
  purchase create/update/delete, recipe edits, expense entries, and advances
  with actor, timestamp, reference, and full before/after details. Buyer accounts
  cannot read the activity API. The log starts with this deployment and can be
  filtered and paged by the manager.
- Pre-migration database backup:
  `20261021_150614-frontend-database.sql.gz` in the site's private backups.
  Previous backend files: `/root/buyer-expenses-activity-backend-before-20261021.tar.gz`.
  Previous panel: `/var/www/one-cafe-before-buyer-expenses-20261021`.
- `bench --site frontend migrate`, the dedicated advance-account setup, the
  panel build, and all 32 Python tests passed. Live checks as a buyer posted
  sample expense and advance Journal Entries and logged purchase
  create/update/delete and a recipe save; every sample transaction was rolled
  back and its records verified absent. The manager could read activity while
  the buyer was denied.

## 2026-10-21: shared purchase desks

- Both existing purchase manager accounts now have Restaurant Purchase Manager
  and Cafe Purchase Manager roles. Each can use both purchase register tabs,
  the purchase-only calendar, and the recipe editor. Neither has manager access.
- The buyer calendar uses `purchasing.calendar_month`, which returns only
  purchases in the caller's granted desks; it does not query sales, cheques,
  staff, or accounting. The assistant accepts either desk and asks which one
  to use before preparing an ambiguous purchase.
- A fresh database backup was saved as
  `20261021_120312-frontend-database.sql.gz`; backend files are archived at
  `/root/purchase-shared-backend-before-20261021.tar.gz` and the previous panel
  at `/var/www/one-cafe-before-shared-purchase-20261021`.
- Build and all 32 Python tests passed. A live read-only smoke
  check as each account confirmed both desks, recipe access, one calendar day,
  and denial of manager access. HTTPS `/calendar` returned 200.

## 2026-10-18: dashboard, calendar, cheques and voice

- Agent chat accepts one image or file per message. Images (JPEG, PNG, WebP,
  GIF) and PDFs (up to eight pages) are read by the configured vision model;
  TXT, Markdown, CSV, JSON, DOCX and XLSX are extracted in memory on the server.
  The assistant retains a short extracted context for follow-up messages in
  the browser session. Uploads are limited to 4 MB (images 3 MB) and are not
  stored as Frappe File records. Synthetic image, CSV and PDF messages returned
  live agent replies and attachment context; DOCX and XLSX extraction passed
  inside the deployed app. The panel build and HTTPS check also passed.
- Spoken replies now default to the Nova voice with warm Persian delivery;
  users can select Marin, Cedar, Nova, or Coral in the assistant. Replies over
  130 characters generate an opening clip and a continuation concurrently so
  playback begins after the shorter clip is ready. The browser still waits for
  each clip before playing it; this is not continuous audio streaming.
- Live timing of a short Persian Nova sample: `gpt-4o-mini-tts` returned its
  first audio bytes in 2.1 s and finished in 2.9 s; `tts-1` took 2.3 s and
  3.7 s respectively. Kept the better sounding model rather than changing to
  the slower alternative on this server. Final panel and speech API checks
  passed; perceived start time for long replies needs a user-side check.
- The live panel now embeds the calendar on the dashboard, offers category and
  recent-order detail there, shows registered customer/cashier names, and no
  longer shows the busy-hours card. Restaurant and cafe purchase views and
  calendar totals are separate.
- The cheque screen shows issued cheques. Clearing a regular cheque requires
  selecting a cash/bank account and counterpart account; one submitted Journal
  Entry is linked to the cheque. A due alert persists until a submitted entry
  exists. Existing cleared cheques without entries still need this action.
- Persian voice input uses the server-side audio transcription API; spoken
  replies use the server-side speech API. The site's existing `ai_api_key`
  remains server-side. Per-day caps are 80 transcriptions and 120 speech clips.
- Pre-deployment database backup: `20261018_171556-frontend-database.sql.gz` in
  the Frappe site's private backups directory. File backup:
  `/root/one-cafe-before-voice-20261018-files.tar.gz`; previous web root:
  `/var/www/one-cafe-before-voice-20261018`.
- `bench --site frontend migrate`, panel build, live VPS checks, dashboard,
  calendar, cheque APIs and a short Persian speech/transcription round trip
  all succeeded. A real cheque settlement was not posted as a test.
The root domain remains on Vercel. The VPS runs Ubuntu 24.04, Docker Engine,
Frappe/ERPNext v16, MariaDB, Redis, and the `cafe_app` bind-mounted from this
repository. Nginx serves the production Vue build and proxies API requests to
Frappe on `127.0.0.1:8080`. Certbot manages the TLS certificate.

## Locations on the VPS

- Project checkout: `/opt/mamad`
- Frappe Docker checkout and Compose config: `/opt/frappe_docker`
- Vue production build: `/var/www/one-cafe`
- Nginx site: `/etc/nginx/sites-available/onecafe`
- ERPNext site name: `frontend`
- Administrator password: `/root/one-cafe-admin-password` (root-only)
- Six-hour backup schedule: `/etc/cron.d/one-cafe-backup`
- Backups: `sites/frontend/private/backups` in the Frappe `sites` Docker volume

The 2 GB VPS has a 4 GB swap file. Gunicorn runs one worker with two threads,
and MariaDB has a 128 MB InnoDB buffer pool. This is a temporary setup for light
use. The backup schedule stores copies on the same VPS; export a current backup
before deleting the VPS.

## Checks and operations

```bash
cd /opt/frappe_docker
docker compose -p cafe -f compose.cafe.yaml ps
docker compose -p cafe -f compose.cafe.yaml logs --tail 100 backend
docker compose -p cafe -f compose.cafe.yaml exec -T backend bench --site frontend doctor
python3 /root/verify-vps.py
```

The deployed `cafe_app` uses the source at `/opt/mamad/apps/cafe_app`. The
warehouse fallback fix in `cafe_setup.py` must be kept when updating that
checkout. The production Vue build was made with `node node_modules/vite/bin/vite.js
build` from `panel/` with demo mode off.

## SepandYar and AI state (2026-09-27)

- `cafe_app.api.sepehryar.sync_products` acknowledges the installed desktop
  client but never writes Item records. The desktop app still calls it before
  `import_sales`; a successful no-op response lets order uploads continue.
- Existing SepandYar products and historical sale item snapshots were repaired
  from the 161-product UTF-8 export. Run
  `bench --site frontend execute cafe_app.product_name_repair.audit_names` for
  a read-only count and sample.
- When a future sale contains a previously unseen source item ID, order import
  creates a generic Persian placeholder so the order is not lost. Repair its
  name from a fresh source export when available.
- The agent is configured for `gpt-6-luna` with a 300,000 reserved-token daily
  cap, 800 completion tokens per call, and at most 3 calls per chat. Its key is
  stored server-side. `ai_enabled=1` was enabled after approval and a live
  authenticated chat request passed. See `deploy/AI-SETUP.md`.

## Installed desktop app (2026-09-27)

- The existing version 0.2.1 starts with Windows sign-in and checks for new
  SepandYar sales every minute while running. It uses the panel's persistent
  Electron session for upload authorization.
- A successful manager login inside the app now issues a signed, HttpOnly,
  Secure, 90-day `one_cafe_device` cookie. When the regular session expires,
  `session.boot` restores it without another password prompt; explicit logout
  removes the device cookie. The signing key stays in the VPS site config.
- The live app still returned HTTP 401 from two source IPs after this server
  update. One login on each installation is required to issue its device
  cookie; do not treat sync as resumed until `session.boot` and `import_sales`
  return 200 in the access log.
- The hosted panel caps startup session check at 6 seconds and retries after
  network failure. Its login animation uses a lighter fallback inside Electron.
  Nginx gzips static JS/CSS and caches hashed assets. No Windows installer
  change was needed for these improvements.
- Use `/downloads/Check-OneCafeConnection.ps1` on any Windows network where
  the site fails. It checks DNS, TCP, HTTPS, TLS timing, and the guest API
  without reading local business data or credentials.

## iPhone Home Screen app (2026-09-27)

- The live site now serves `/manifest.json`, `/one-cafe-icon.png`, `/sw.js`, and
  `/offline.html`. The manifest launches the panel in standalone mode with the
  ONE CAFE icon and dark theme. Safari: Share → Add to Home Screen → enable
  Open as Web App → Add.
- The service worker caches only the generic offline page and logo. It never
  caches authentication, API responses, orders, or other business data. The
  panel still needs an internet connection for current data.
- Live checks returned HTTP 200 for the root page, `/login`, manifest, icon,
  service worker, offline page, and `/api/method/ping` after publication.
- Web Push subscription and delivery are not implemented for this PWA yet;
  installing it does not enable notifications.

## Desktop sync authentication audit (2026-09-28)

- The original 0.2.1-backfill installer on the Desktop was inspected without
  launching it. Both its panel and sales uploader use `persist:one-cafe`, and
  uploader requests use `credentials: include`.
- An isolated Electron 44.4.5 test confirmed that `Session.fetch` stores and
  sends a SameSite=Lax cookie in this configuration. This does not inspect the
  cafe PC's actual browser profile.
- A live HTTPS test with an isolated signed desktop cookie and an invalid sid
  returned 200 for session restoration, the subsequent boot, and an empty sales
  import. Logout removed that test client's device cookie; the next boot was
  denied with 401. No invoices were created.
- At 15:41–15:45 UTC, the failing 0.2.1 requests contained neither `sid` nor
  `one_cafe_device`. Cookie absence is established; its cause is not. Do not
  attribute it to cashier logout or a particular server change without evidence.
- `cafe_desktop_auth.log` now records only cookie presence/validity booleans,
  request metadata, and signing-key presence on failed desktop boots. It never
  logs cookie values or the signing key. Tests cover credential redaction and
  preservation of authentication denial if logging fails.
- Product sync still returns a successful no-op. Missing authentication remains
  the current stop before SQL reads in the old client; the cafe upload has not
  been restored by this audit. A server restart alone does not reconstruct an
  absent device credential.

## Independent device sales sync (2026-09-28, version 0.3.1)

- New POST endpoints `sepehryar.device_boot` and
  `sepehryar.device_import_sales` require a valid `X-OneCafe-Device-Token` for an
  enabled enrolled device. The enrolling user must still be an enabled manager.
  They issue no panel login and return no CSRF token.
- The 0.3.1 importer uses that token through requests with `credentials: omit`.
  It skips disabled catalog queries and preserves its acknowledged cursor.
  Existing 0.3.0 device registrations are reused; a new 0.2.1-to-0.3.1 install
  needs one manager login to enroll. Panel logout does not revoke the separate
  device registration. Disable the device on the VPS to revoke it.
- Eleven desktop tests pass, including logged-out panel, process restart,
  failed upload retry, rejected device and concurrent enrollment. Six backend
  auth/privacy tests pass. The packaged ASAR contains the new adapter and
  single-instance lock.
- Live HTTPS probes returned 200 for device boot and an empty upload without a
  browser session, 401 without a token and 401 after disabling the probe device.
  No invoice was created. The probe device remains disabled.
- Installer: `/downloads/ONE-CAFE-Setup-0.3.1.exe`, 111565297 bytes,
  SHA256 `7691daf53140e02ea247a26bfdc8047296b2a95c3d47a9311fb5e85bf4fcec25`.
  The main cafe's 0.2.1 sync is not proven restored until installation/enrollment
  and actual sales uploads are observed. Do not equate the HTTP probe with a
  successful read from the cafe's SQL Server.

## Café source verification and historic recovery (2026-09-28)

- The actual café PC `DESKTOP-GCTP2FH` enrolled version 0.3.1. Its enabled
  device identity is `87110e0744e13a450971e7b70298f60d9c97209190caf10a9ff6e3edd19fccfd`.
  Read-only remote jobs ran successfully against `.\\SEPANDYAR2014`, database
  `Sepand_One_1405`, including Unicode catalog and compressed weekly exports.
  Subsequent heartbeat was observed at 22:17:48 Tehran. This is actual café
  execution, not the isolated auth probe above.
- Source item IDs repeat across warehouses. Warehouse 3 is the actual menu;
  warehouse 2 is raw materials. SKU 64 is `چاي دست چين`; SKU 32 is
  `ايس امريكانو 80/20`. Source names were read with .NET SqlClient Unicode
  rather than the old ambiguous MAX(Name) catalog query.
- An audited CLI repair changed 115 Item labels and 553 historical invoice
  labels. No existing invoice quantities, rates, amounts, dates, statuses,
  recipes or item prices were changed. Two old invoice rows absent from their
  current SQL source rows were left unresolved rather than guessed.
- `Day_Factor_Log` / `Day_TR_Log` contain archived invoices. 864 missing,
  noncancelled archived receipts from 2026-09-19 through 2026-09-25 were
  imported; 225 existing receipts from 2026-09-26/27 were skipped. Source
  markers prevent repeat insertion. Every new row's item identity, Unicode
  name, quantity and amount, plus invoice total/date/submission, were verified.
  Final audit: complete, 864 created, 225 skipped, zero missing, zero import
  errors, zero new invoice discrepancies, zero old financial changes.
- The live menu returns 128 menu products. Source raw-material entries are
  hidden without deleting Item records; corrected legacy tea/americano labels
  now display normally, while the unresolved wrong-label row stays marked.
- Existing source discrepancies remain deliberately untouched: 27 stored
  invoice totals differ from the current SQL totals, and factor 23050 exists
  on this server although its SQL header is cancelled. These require a separate
  financial correction decision; do not describe existing revenue as fully
  reconciled. The old desktop likely captured some still-changing bills;
  that cause has not been established for every discrepancy.
- Private audit artifacts are under `/opt/mamad/reports` and site private
  `files/source-reconciliation`; local copies are in `deploy/reports`.
  The Windows application must stay running under a signed-in Windows user;
  locked screen and tray mode work. Power-off, logout or quitting the app
  stops remote polling and sales sync. The representative is not required
  for the proven catalog/backfill operations.

## Source menu categories and simplified sales display (2026-09-28)

- A read-only remote query returned the actual warehouse-3 `TblKala.GroupCode`
  and `TblGroupKala` classifications. All 128 menu products are assigned to
  16 Persian categories. Four uncategorized entries were explicitly assigned:
  fork to packaging/services, chocolate to add-ons, bread and egg to breakfast.
  Source group 013 contains only packaging despite its stale caramel label;
  it is displayed as packaging/services.
- The CLI category repair updated 221 source Item records (both warehouse
  variants and legacy IDs) and 2528 invoice item category snapshots. The
  category audit preserves every old group in the site's private files.
  Historical dashboard category shares now use the repaired categories.
  New imported products receive their verified category at creation; manual
  menu edits remain possible and product catalog sync remains disabled.
- Imported order lists/details, returns, dashboard payment totals and printable
  receipts display `سپهریار`. Their original Mode of Payment/accounting records
  were not rewritten. Sales UI labels this field `منبع فروش`; purchase/expense
  payment methods retain their actual meaning.
- Menu category filters wrap into visible rows and show product counts.
  Shifts are hidden in navigation and the retained `/shifts` route redirects
  to dashboard through `meta.hidden`. Shifts source and data are preserved.
- Live API verification returned 128 menu entries in all 16 categories, zero
  imported orders showing other payment labels, and a single SepandYar sales
  total. Vue type checking/build and four device-auth tests pass. The repeated
  financial audit reported zero old financial changes and zero new receipt
  discrepancies. The updated production panel is deployed under
  `/var/www/one-cafe`; no Windows installer update is required.

## 2026-09-29: source payment and current invoice projections

- `source_payment_device` explicitly enables the enrolled café PC only. The
  existing Windows 0.3.1 poll receives a predefined .NET SqlClient SELECT job
  every five minutes. No Windows reinstall or source database write is needed.
- `Cafe Source Payment` snapshots record source totals, received amounts,
  payment methods, original credit, current invoice items, source time and job.
  Current methods are read from `TblFactorAvamelNasiyeForush`: پوز ملت, وجه نقد,
  کارت به کارت. `Day_TR.IdAmel=99` is a customer receivable, not cash received.
- `IsTasviye` and digimall's generic payment_state include credit postings and
  cannot prove that money was collected. Archived Day FactorIDs map to general
  accounting invoice numbers through `TblFactorOnvan.FactorCust`, not GUID.
- Customer receipts with `TR.Factor=0` have no invoice allocation. Their amount
  is never distributed by a guessed FIFO rule. Invoice outstanding is unknown
  when those receipts exist and account debt remains. Original credit and the
  full customer balance are displayed separately. Complete verified customer
  account clearance can settle the credit; unposted daily credit is included.
- Source queries reproduce the native `SumMabKol` rule for totals and extract
  product names with warehouse AND SKU. Unknown/removed source headers cannot
  preserve a stale Paid status. Results are bounded, validated, idempotent and
  rejected if they target an unauthorized device or unrequested invoice.
- The old importer captures a submitted ERP invoice once. Orders and dashboard
  now project the latest verified POS amounts/items instead of that initial
  snapshot. Original ERP invoices, GL, payment rows and inventory postings are
  preserved; these read projections do not repair historic ERP accounting or
  stock postings. That would require a separate accounting reconciliation.
  Imported invoice returns must be recorded in SepandYar; the panel and API
  prevent refunding a stale initial ERP snapshot as if it were the current bill.
- Debt and today's invoices are prioritized each round, with remaining batch
  capacity rotating through older invoices. A 500-invoice cap bounds reads.
  Source checks require the café PC and app to remain online. The panel refreshes
  after a changed payment revision through its existing fifteen-second pulse.
- Real café execution imported full item snapshots for 1276 existing orders.
  Fourteen payment tests and four device authentication tests pass. Live API
  checks confirm identical order/dashboard totals and no changes to stored
  invoice amounts, line items or ERP payment entries. Audits are private in
  `sites/frontend/private/files/source-reconciliation/`.
- Invoice `ACC-SINV-2026-01240` initially held only املت وان (339000 تومان).
  Its current four source items total 1023000 تومان: ایس امریکانو 239000,
  آب معدنی 35000, خلیج 410000, املت وان 339000. Direct card transfer is 374000
  تومان and original credit 649000 تومان. Customer receipts are unallocated,
  so 649000 is not asserted to be the exact remaining debt of this invoice.

### Payment clarity and credit customers — 2026-09-29

- Source report version 3 includes customer membership ID, UTF-8 name, unique
  receivable account key, source FactorID and the exact method/account catalog.
  Names are joined from TblPerson; duplicated identical first/last names are
  displayed once. No phone numbers or unrelated personal fields are collected.
- Customer receivables under account 110 can use more than one Moin (the live
  source uses 1 and 4). New accounts with unposted daily debt and no general-ledger
  history are included. Shared or unmatched accounts cannot establish settlement.
- Orders supports customer name/ID search and separate filters for Paid, Credit,
  Partial, Unpaid, account allocation review, unknown/waiting and Cancelled.
  Missing payment snapshots also appear under the unknown/waiting filter.
- The credit customer report aggregates all selected invoices, independently of
  the 40-row display page. The latest verified account balance is counted once
  per account; it covers the entire source account rather than the date filter.
  Unknown invoice outstanding stays null and is never counted as zero debt.
- Unallocated source account credits use a distinct review badge. Each invoice
  explains the evidence, customer, original credit, known invoice remaining,
  full account balance and time of the latest read. Data older than 15 minutes
  is explicitly identified. New invoices awaiting a payment read are identified.
- Source method 3 is named کارت به کارت and maps to the account صادرات پوز;
  both names are displayed. This proves the account mapping, not the physical
  terminal used. The outside terminal cannot be separated from transfers without
  a distinct source method or another verified transaction discriminator.
  Method 10 exists but has no observed receipt in the inspected recent history;
  it is not relabelled as an outside terminal. New source methods are read each cycle.
- Nineteen payment/processing tests pass, as do frontend type checking and builds.
  Live acceptance checked 1283 invoices, all 9 credit customer accounts, mutually
  exclusive payment filters, exact invoice 1240 identity/account mapping and
  identical dashboard/order totals. Existing submitted ERP financial data remains
  unchanged. Private audit: payment-clarity-20260929.json.
- Installed Windows app 0.3.1 continues to execute the predefined source read;
  no app update is required. Each cycle requires the café PC/app to remain online.

## 2026-10-06: staff contracts, purchase desks and recipe costs

- New DocTypes: `Cafe Employee` (+ `Cafe Employee Contract`), `Cafe Purchase`
  (+ `Cafe Purchase Item`), `Cafe Recipe` (+ `Cafe Recipe Row`). Created with
  `bench migrate` after a database backup (`20261005_235653-frontend`).
  Pre-change copies of the edited live files: `/root/cafe_app-pre-staff-buying-20261005.tgz`;
  previous panel entry: `/var/www/one-cafe/index.html.pre-staff-buying-20261006`.
- Panel: `/staff` (manager only) and `/purchases` (the purchase register; the old
  ERP Purchase Invoice page was empty and is replaced).
- Purchase desks share company, accounts and warehouse; only the people differ.
  Users `restaurant.buyer@onecafe.beyondex.one` (role Restaurant Purchase Manager)
  and `cafe.buyer@onecafe.beyondex.one` (role Cafe Purchase Manager) are Website
  Users (no ERPNext desk). Initial passwords: `/root/one-cafe-buyer-passwords`
  (root-only). `cafe_app.access.restrict_buyers` (before_request) refuses every
  API except session boot, the agent chat and `cafe_app.api.purchasing.*`; the
  server forces their desk on every read and write. Their assistant has only the
  purchase tools and a purchasing prompt.
- Purchases are a register only: they are NOT posted to the GL or stock. A purchase
  line linked to an ingredient Item updates that Item's `valuation_rate` from the
  latest comparable purchase (kilo/litre -> gram/millilitre).
- Recipes cost menu items only and never move stock (no Product Bundles).
  Imported by `cafe_app.maintenance.import_staff_recipes_20261005`: 8 staff
  (سمیرا قادری جوان has two contracts), 28 non-stock ingredient Items, recipes
  on 54 existing menu items (both 100 and 80/20 variants). Menu items themselves
  were not modified. Not matched to a menu item: the three sandwiches, آرامش,
  پژواک, سن میلو, آیس چاکلت, آیس لته ماچا, گلد.
- Restarting `backend` again left the frontend nginx container pointing at the old
  backend IP (HTTP 502); `docker compose ... restart frontend` fixes it.

## 2026-10-06: calendar, cheques, recipe corrections

- New `Cafe Cheque` DocType (received/issued; cheque, guarantee cheque or promissory
  note; Pending/Cleared/Bounced/Transferred/Returned/Cancelled) and panel pages
  `/cheques` and `/calendar` (Shamsi month grid, Saturday first). Backup before
  migrate: `20261006_120833-frontend`. Previous panel entry: `index.html.pre-calendar-20261006`.
- `cafe_app.api.daybook.month` returns per day: sales (same projection as the
  dashboard trend), purchases, expense journal entries, cheques due, contract
  starts/ends, Shamsi paydays (contract `payment_day`, from the first month after
  the start) and staff birthdays. `daybook.alerts` lists overdue/near cheques,
  bounced cheques, expiring contracts, paydays and birthdays in 3 days, a quiet
  till (no new Sales Invoice for 2 h between 10:30 and 23:30) and recipe gaps.
  Both are manager-only; purchase managers are refused by the request gate.
- Recipes were corrected from the contract/recipe photos and the café's dictated
  values; where the dictation looked like a dropped/added hundred the sheet value
  was kept (noted on each recipe). `maintenance/recipe_cost_report` and
  `maintenance/sales_without_recipe` are read-only reports.

## 2026-10-06: full-reach assistant, assumed recipe/contract values

- Agent rewritten: 25 manager tools (`agent/reports.py` + `agent/tools.py`): any
  period/day/range incl. Shamsi dates and Shamsi months, category/hour/payment
  breakdown, item sales, order search and detail, expenses, purchases, price
  history, cheques, staff and real paydays, day overview, alerts, menu costing,
  ingredient prices; proposals for expense, waste, purchase, cheque, cheque
  status and ingredient price. Purchase managers get only their desk's
  purchase entry/report/price history; the desk parameter is not offered to them.
- Root cause of the weak answers: the 12,000-byte input cap rejected most
  second requests, and `sales_report` read top items as attributes (crash).
- Limits now: 60,000 input bytes, 5 steps (last one forced to answer), 8 tool
  calls, 1,000 completion tokens, daily cap 1,000,000 tokens. Reservations are
  still byte-based before the call and are corrected to the provider's reported
  `usage.total_tokens` afterwards. Pre-change copy: `/root/cafe_app-pre-agent-20261006.tgz`.
- Gaps filled with assumptions marked «فرضی» on the contract/recipe note
  (missing espresso 32 g / double 35 g, sugar 5 g, payday = start day, cakes as
  bought-ready, add-on syrups 30 g). 74 menu items have a recipe.
