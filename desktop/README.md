# ONE CAFE desktop

Install version 0.3.1 on the same PC as SepandYar. Sign in once inside the app
with an Administrator or System Manager account to enroll this installation.
The device token is encrypted with Windows safeStorage in `remote-agent.json`.
Sales uploads then use that credential independently of the panel login;
panel logout, cookie expiry and restarting the app do not stop an enrolled
device's sales uploads. The app must be running under the same Windows user.
Disabling the device or its enrolling manager account on the VPS stops access.
An existing 0.3.0 enrollment is reused without another login. Version 0.2.1 has
no device token and cannot be repaired into this behavior solely from the VPS.
The app sends sales to `https://onecafe.beyondex.one` over HTTPS; no separate
API key or SQL password needs to be entered.

The local source is SQL Server `.\SEPANDYAR2014`, database
`Sepand_One_1405`. The client invokes the installed `sqlcmd` with Windows
integrated authentication and SELECT queries. It does not copy or edit the
SQL Server data files. Invoice headers come from `Day_Factor`; sale lines come
from `Day_TR` with names joined from `TblKala`. Catalog sync is disabled, so a
catalog query failure cannot stop sales uploads. The accounting balancing
line with `IdKala = 0` is excluded. Products are joined on `IdKala` and
`IdAnbar` so warehouse duplicates do not multiply sale lines.

On first launch it imports all non-cancelled sales in the current
`Sepand_One_1405` database and follows new FactorIDs. The initial backfill may
take hours depending on its size and server speed.
Upgrading from 0.2.0 also resets its source cursor once to backfill the sales
that version skipped; previously acknowledged invoices are deduplicated.
Previously imported FactorIDs are persisted in Electron `userData` at
`sepehryar-sync.json`. The cursor moves only after the server acknowledges the
invoice. The backend checks `[Sepand:1405:<FactorID>]` to make retries safe.
The installed client still calls catalogue sync at startup and hourly, but the
server acknowledges it without writing products. Product names are maintained
on the server from the verified UTF-8 export. Sales sync runs every minute
while the desktop app runs, including when its window is hidden in the system
tray. Very recent invoices wait three minutes so an
open bill is less likely to be imported before completion. The installed app
registers itself to open when Windows signs in. A single-instance lock prevents
duplicate processes under the same Windows profile. The tray menu has an explicit
exit action. The Windows user must be able to run `sqlcmd -E` against the local
instance.

## Remote maintenance in 0.3.0

After one manager sign-in, the app registers this Windows installation with the
server and stores a device-only token encrypted by Windows. It checks for a
maintenance job every 30 seconds and sends the exit code, standard output and
standard error back to the server. The cashier does not approve each job. Jobs
can only be queued from the VPS shell with `bench execute`; the web panel has
no command submission endpoint. Every job is recorded with its script hash,
device, status, times and result. A claimed job is never silently rerun after a
crash. The device can be disabled on the server to revoke access.

PowerShell runs with the rights of the Windows user running ONE CAFE. It cannot
silently elevate through UAC. The desktop app starts at Windows sign-in and
continues polling while its window is hidden in the tray; no user session means
no polling. A queued job waits for the next start. See
`deploy/REMOTE-MAINTENANCE.md` for operator commands and limits.
When SepandYar changes to a new yearly database, the source database setting
must be updated in a future app release.

New items use codes `SEPAND-<IdAnbar>-<IdKala>` and no recipe; legacy codes are
kept when an older client omits the warehouse. Staff can edit
their recipe in the menu page. Imported sales use the source line amount and
the source Jalali date converted to Gregorian. The server rejects an invoice
when the calculated total differs from the source sum. Since source payment
splits are unknown, imported payments go to a separate **تسویه سپهریار**
clearing account rather than Cash or Credit Card.

## Build on Windows

```powershell
cd desktop
pnpm install
$env:ELECTRON_BUILDER_CACHE = Join-Path (Get-Location) '.cache/electron-builder'
pnpm test
pnpm dist:win
```

The NSIS installer is in `desktop/dist/`. It is unsigned, so Windows may show
a publisher warning. The live panel is shown in a sandboxed `WebContentsView`
without Node access. Only the local shell can trigger a manual sync.
