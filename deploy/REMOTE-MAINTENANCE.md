# ONE CAFE remote maintenance

Version 0.3.1 of the Windows app must be installed and started on the café PC.
Sign in inside the app once with a ONE CAFE Administrator/System Manager account.
The app registers the device and then polls every 30 seconds. The setup panel
shows `مدیریت از راه دور فعال` and its device ID when connected. No cashier
approval is requested for each subsequent job.

In 0.3.1 the same encrypted device registration authorizes sales sync every
minute without a panel login. Existing 0.3.0 registrations are reused. The
server validates the enabled device and the enrolling manager's current rights
for sales; no panel session is issued by the device-only endpoints. The old
0.2.1 installation has no registration token and needs this installer plus one
manager sign-in before it can use that path.

The app runs as the signed-in Windows account. It cannot bypass Windows UAC or
run before anyone has signed in. If the PC is off, the app is quit, or Windows
is logged out, queued work waits until the app starts again. A locked Windows
session is fine. Give that account only the rights required by the jobs.

## On the VPS

Use `bench execute` from the backend container or bench environment. The web
API deliberately does not allow a browser to queue scripts. Put the exact
PowerShell code in a UTF-8 `.ps1` file on the VPS; do not paste scripts into a
shell argument. Keep the file private if it contains sensitive instructions.

```bash
cd /opt/frappe_docker
docker compose -p cafe -f compose.cafe.yaml exec -T backend \
  bench --site frontend execute cafe_app.api.desktop_remote.queue_script \
  --kwargs '{"script_path":"/home/frappe/frappe-bench/apps/cafe_app/cafe_app/maintenance/check.ps1","timeout_seconds":120}'
```

The command returns a job ID. To read the result:

```bash
docker compose -p cafe -f compose.cafe.yaml exec -T backend \
  bench --site frontend execute cafe_app.api.desktop_remote.job_result \
  --kwargs '{"job_id":"JOB_ID_FROM_ABOVE"}'
```

If more than one enabled device is registered, add `"device_id":"EXACT_ID"`
to the queue command. Device IDs can be read in the `Cafe Desktop Device`
DocType as a System Manager. Set `enabled` to 0 there to revoke a device.

Each job is capped at 32 KiB of UTF-8 PowerShell, 5 to 600 seconds of runtime,
and roughly 60 KiB each of output and errors. The client validates a SHA-256
digest of the script over HTTPS before execution. All job contents and results
are visible to server administrators; avoid printing passwords or access keys.

The agent writes a temporary `.ps1` under the current user's temp directory,
executes it with Windows PowerShell, and removes only that temporary file. It
does not modify SepandYar data unless an operator explicitly submits a script
that does so. Use `SELECT` only for data diagnosis.
