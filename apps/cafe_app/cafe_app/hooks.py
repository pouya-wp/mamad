app_name = "cafe_app"
app_title = "Cafe"
app_publisher = "Pouya"
app_description = "Cafe management on top of ERPNext: inventory, recipes, accounting and a dedicated admin panel"
app_email = "beyondexai@gmail.com"
app_license = "unlicensed"

required_apps = ["erpnext"]

# Installation
# ------------
# The root Item Group is created by ERPNext's setup wizard, so café defaults are
# seeded either right after install (wizard already done) or when the wizard completes.

after_install = "cafe_app.install.after_install"
setup_wizard_complete = "cafe_app.install.setup_wizard_complete"
