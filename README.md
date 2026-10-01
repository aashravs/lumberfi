# Lumberfi Commission Dashboard

## Overview
Bare-bones internal commission platform built using Google Apps Script,
Google Sheets, HTML, CSS and JavaScript.

## Features
- Role-based access: AE, Manager, Admin
- Server-side data filtering
- Commission calculation
- Annual, monthly and quarterly payouts
- Advance recovery
- Cancellation clawbacks
- Admin recalculation
- Admin CSV deal upload
- Dashboard for paid and upcoming payouts

## Roles

AE
- View own deals
- View own payouts

Manager
- View team deals
- View team payouts

Admin
- View all data
- Recalculate commissions
- Upload deal dump

## Test Accounts

| Role | Email |
|---|---|
| AE | ae1@test.com |
| Manager | manager@test.com |
| Admin | admin@test.com |

## Assumptions
- Commission plan applies to deals closed from 1 Jul 2026 to 30 Sep 2026.
- Working days are Monday-Friday; holidays are not excluded.
- CSV is the supported upload format.
- Google Sheets acts as the backend datastore.
- Access is enforced server-side.

## How to Run
1. Open the deployed Google Apps Script web app.
2. Sign in using an authorized Google account.
3. Admin can upload a CSV deal dump or recalculate commissions.
