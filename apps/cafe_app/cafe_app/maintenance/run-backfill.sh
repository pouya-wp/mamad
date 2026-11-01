#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/frappe-bench
bench --site frontend execute cafe_app.maintenance.reconcile_source.backfill --kwargs '{"catalog_path":"/home/frappe/frappe-bench/sites/frontend/private/files/source-reconciliation/catalog.json","week_path":"/home/frappe/frappe-bench/sites/frontend/private/files/source-reconciliation/week.json","extras_path":"/home/frappe/frappe-bench/sites/frontend/private/files/source-reconciliation/extras.json","progress_path":"/home/frappe/frappe-bench/sites/frontend/private/files/source-reconciliation/backfill-progress.json"}' > /home/frappe/frappe-bench/sites/frontend/private/files/source-reconciliation/backfill-run.log 2>&1
