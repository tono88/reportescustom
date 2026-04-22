# Bank Reference Duplicate Check (Odoo 18 Community)

What it does:
- Checks duplicate `bank_reference` when **posting a payment** (account.payment.action_post)
- Checks duplicate `bank_reference` in **Register Payment** wizard before creating payments
- If duplicates are found, shows a modal with:
  - message
  - HTML table listing existing payments with clickable links
  - buttons: Proceed / Close

Note:
- The module adds a `bank_reference` field to `account.payment.register`. If you already have that field from another customization, remove the line in `models/account_payment_register.py` to avoid field duplication.
