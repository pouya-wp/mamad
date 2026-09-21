# Cafe App

Custom Frappe app on top of ERPNext v16 for running a café.

- Inventory: raw materials (coffee beans, milk, cups…) tracked in ERPNext Stock
- Recipes: each menu item is a non-stock Item with a **Product Bundle** of its ingredients, so every POS / Sales Invoice sale deducts the ingredients from stock
- Accounting: ERPNext Accounts (café-specific requirements TBD)
- Admin panel: dedicated Persian workspace (TBD)

## Install

```bash
bench get-app <repo-url-of-cafe_app>
bench --site <site> install-app cafe_app
```

Requires `erpnext`.
