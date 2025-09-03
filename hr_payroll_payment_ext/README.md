# Payroll Payments from Batch (Community) — Odoo 18

This module lets you create **Account Payments** (including the ability to pick a **check** method if your bank journal has it)
directly from an **hr.payslip.run** (payroll batch).

## Features
- Add a **Payments** tab in the payroll batch.
- Choose **Payment Journal**, **Payment Date**, and **Payment Mode** (per employee or single batch payment).
- Button **Create Payments** to generate and (optionally) post payments.
- Smart button to **View Payments** created from the batch.
- Payment state on the batch: *No Payment → To Pay → Paid*.

> Notes
> - The **per employee** mode creates one `account.payment` per employee using the employee's *Private Address* (`address_home_id`) as the partner.
> - The net amount per payslip is taken from the line with code **NET / NETO**; adapt in code if your structure uses other codes.
> - To print checks, your **Bank journal** must include a **Check** outbound payment method (Community-compatible check printing module if applicable).
> - Posting the payments marks the batch as **Paid** (you can override with the *Mark Paid* button).

## Installation
1. Copy `hr_payroll_payment_ext` into your addons path.
2. Update apps list and install.
3. On a payroll batch, go to the **Payments** tab, pick journal and date, and click **Create Payments**.

## Compatibility
- Odoo **18.0 Community**.
- Depends on: `hr_payroll`, `account`, `hr`.