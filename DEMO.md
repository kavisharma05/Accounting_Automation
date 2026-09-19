# Prototype demo — recording script

Use this as a teleprompter. Target length: **4–6 minutes**. The owner story is Home → Pay → Reports. Do not open Accountant tools unless asked.

**Dashboard:** https://accountingautomation-production.up.railway.app/  
**Login:** `admin@pilot.local` / `pilot-admin-change-me`  
Open the **root URL** (the trailing slash). Do not type `/login` into the address bar.

### Live books (already seeded)

| Item | Value |
|------|--------|
| Purchase | `BR-2026-00001` — Sharma Computers — **₹54,870** — posted |
| Invoice date | `2026-08-08` |
| Journal | `JE-000001` |
| Payment amount | `54870` |
| Payment date | `2026-09-19` |
| Payment UTR | `UTRDEMO001` |
| Bank file | `scripts/demo-bank-statement.csv` |
| GSTR period | **From `2026-08-01` To `2026-09-30`** (the purchase is in August) |

The product story in one line: *send a bill photo, confirm the numbers, the books update, the CA gets the ledger.*

---

## Process chain (what you are showing)

```
Photo of vendor bill (Home)
        ↓
App reads it (vendor, GST, total)
        ↓
You tap Confirm
        ↓
Books update (you owe the vendor)
        ↓
Optional: Pay (you paid them)
        ↓
Reports: ledger + GST sheet for the CA
```

AI never posts. Confirm is the only required click.

---

## Before you hit record

Do this **off camera**. Dry-run the full click path once.

1. Chrome incognito, 1920×1080, bookmarks hidden, notifications off.
2. Confirm the site is up:

   ```bash
   python scripts/verify_production.py --login admin@pilot.local --password 'YOUR_PASSWORD'
   ```

3. Seed the hero purchase into the **same org the dashboard uses** (do not use `pilot_ai_test.py` — that creates a throwaway org you cannot log into):

   ```bash
   python scripts/demo_prep.py --invoice scripts/real-gst-invoice.jpg --password 'YOUR_PASSWORD'
   ```

   Add `--skip-confirm` if you want **Confirm & post** to happen on camera.

4. Keep the printed cheat sheet on a second screen. You will need:
   - purchase invoice number + total
   - payment date = today
   - payment amount = that total
   - reference `UTRDEMO001`
   - `scripts/demo-bank-statement.csv` (already written to match)

5. Have these files in an easy folder (Desktop is fine):
   - `scripts/real-gst-invoice.jpg` (or `scripts/sample-invoice.jpg`)
   - `scripts/demo-bank-statement.csv`
6. Sign out so the recording starts on the login screen.
7. If **Upload bill** is not on the Invoices page yet, you are on the build *before* that button — still record; `demo_prep.py` already put the purchase on the books.

---

## Shot list

| # | Time | Screen | You click | You say |
|---|------|--------|-----------|---------|
| 0 | 0:00 | Login | Sign in | “Owners send bill photos on WhatsApp. Same thing here: photo in, confirm, books update.” |
| 1 | 0:15 | Home | Drop/upload a bill (or show one already waiting) → **Confirm** | “The app reads the vendor and amount. Nothing is booked until I say yes.” |
| 2 | 1:30 | Home | Pause on unpaid + Just booked | “After confirm, you owe that vendor. The journal is already balanced.” |
| 3 | 2:00 | Pay | **Record payment** → Sharma Computers → `54870` → `2026-09-19` → `UTRDEMO001` → apply to `BR-2026-00001` → **Save** | “When they pay, one extra click. That is optional.” |
| 4 | 3:00 | Reports | From `2026-08-01` To `2026-09-30` → Load GST → **Send ledger to CA** | “The CA gets the ledger and GST sheet. The owner never opens Tally.” |
| 5 | 4:00 | — | Stop | “Photo in. Confirm. Books. Ledger out.” |

Sales, notes, bank, and compliance are under **Accountant tools**. Skip them unless someone asks.

---

## Numbers to type (do not improvise)

| Field | Value |
|-------|--------|
| Sales customer | `Retail Customer` |
| Sales invoice | `SI-DEMO-001` |
| Taxable / tax | `10000` / `1800` |
| Credit note | `CN-DEMO-001` |
| Note taxable / tax | `1000` / `180` |
| Payment reference | `UTRDEMO001` |
| Payment amount + date | From `demo_prep.py` cheat sheet — **must match the bank CSV** |
| TDS section | `194C` |

If you change the payment amount or date, edit `scripts/demo-bank-statement.csv` before the Bank shot. Reconcile matches **amount + date** only.

---

## Talking points (use, don’t invent)

- **Problem:** owners WhatsApp bill photos; someone retypes them into Tally; GST and the CA pack are a month-end scramble.
- **Rule:** AI proposes, the accounting engine posts. A retried job cannot double-post.
- **GST:** input tax on purchases, output tax on sales, net on the GSTR-3B card.
- **Honest prototype limits (if asked):** e-invoice IRN is sandbox; GSTR is a worksheet, not a GSTN filing; WhatsApp is the intended capture channel — the dashboard upload is the same pipeline.

Do **not** open `/docs` or a terminal on camera unless someone asks how capture works without WhatsApp.

---

## If something breaks mid-take

| Symptom | Fix (cut, or keep talking) |
|---------|----------------------------|
| Login fails | Password was rotated — run `scripts/update_pilot_password.py` on the Railway API shell, then `verify_production.py --login …` |
| Overview empty | `demo_prep.py` did not run against this org |
| Upload / extract hangs | Wait up to 3 minutes; if it fails, skip to the purchase `demo_prep` already posted |
| “Mock Vendor / 59000” | Document AI is still on the mock adapter — say “structured proposal from the bill” and continue |
| Duplicate invoice | Same photo was uploaded before — search that number and continue |
| Payments has no vendor | **Quick add vendor**, or go back to Invoices and confirm the purchase first |
| Bank matches 0 | Payment date or amount ≠ CSV row |
| GSTR all zeros | Period must include today’s invoice dates |

Record the failed take anyway if the words were clean — jump-cut to a retry of that one screen.

---

## Recording setup

- Tool: Windows Game Bar (`Win+G`) or OBS. 1080p, 30 fps.
- Mic: close, then a 5-second silence at the start for noise reduction.
- Cursor: slow. Pause after every success banner so it is readable.
- Do not scroll-spam. One deliberate scroll if the table is long.
- After the take: trim the login wait and the Excel download dialog.

---

## Local recording (if production password or AI is wrong)

```bash
docker compose up --build -d
docker compose --profile tools run --rm seed
python scripts/demo_prep.py --base-url http://localhost:8000 --invoice scripts/sample-invoice.jpg
```

Open http://localhost:8000 — same login as seed (`admin@pilot.local` / `pilot-admin-change-me`).

To record the new **Upload bill** button, this local/rebuild path is required until that UI is deployed.
