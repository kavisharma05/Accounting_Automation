# Prototype demo — recording script

Use this as a teleprompter. Target length: **7–9 minutes**. One take, left-to-right through the sidebar.

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

The product story in one line: *a GST-registered SMB photographs a vendor bill, the system proposes a double-entry, a human confirms, then sales, payment, bank, GST, and a ledger for the CA all sit on the same books.*

---

## Process chain (what you are showing)

```
Photo of vendor bill
        ↓
AI extraction (GSTIN, lines, tax, total)
        ↓
Human confirm  →  purchase invoice posted  →  Dr Expense / Dr ITC / Cr Payable
        ↓
Sales invoice created & posted  →  Dr Receivable / Cr Revenue / Cr Output GST
        ↓
E-invoice IRN (sandbox)
        ↓
Vendor payment + optional TDS  →  Dr Payable / Cr Bank
        ↓
Credit note (returns / adjustment)
        ↓
Bank CSV import + auto-reconcile (amount + date match)
        ↓
GSTR-1 / GSTR-3B worksheet + Excel
        ↓
Compliance calendar (GST/TDS due dates)
        ↓
Ledger Excel for the CA
```

AI never posts. The domain layer checks debit = credit before every journal.

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
| 0 | 0:00 | Login | Sign in | “This is the books of a typical GST-registered Indian SMB. The owner sends bills on WhatsApp or uploads a photo. We extract, they confirm, the ledger posts.” |
| 1 | 0:20 | Overview | Pause on the four cards | “Pending approvals, outstanding invoices, rupees still unpaid, and the latest journal entries. Debit always equals credit.” |
| 2 | 0:45 | Invoices | Search the vendor / invoice number. If recording capture live: **Upload bill** → pick the photo → wait → **Confirm & post** | “A vendor bill arrived as a photo. AI proposed the GSTIN, taxable, and tax. Nothing hit the ledger until confirm.” |
| 3 | 2:00 | Sales | **New sales invoice** → quick-add customer `Retail Customer` → number `SI-DEMO-001` → taxable `10000` tax `1800` → **Create** → **Post** → **E-invoice** | “Same books, the other side: we raise a sales invoice, post it, and generate a sandbox IRN.” |
| 4 | 3:30 | Invoices | Filter or search `SI-DEMO-001` | “Purchase and sales in one list, with outstanding.” |
| 5 | 3:50 | Payments | **Record payment** → vendor **Sharma Computers** → amount `54870` → date `2026-09-19` → reference `UTRDEMO001` → apply to `BR-2026-00001` for `54870` → **Save** → **Apply 194C** | “Payment knocks down the payable. TDS is computed on the payment, not typed into a spreadsheet.” |
| 6 | 5:00 | Notes | Credit note `CN-DEMO-001` on `SI-DEMO-001` → taxable `1000` tax `180` → reason `Goods returned` → **Create & post** | “Returns and adjustments are notes against the original invoice, not a deleted row.” |
| 7 | 5:40 | Bank | Register bank if asked → import `demo-bank-statement.csv` → **Auto-reconcile** | “Statement line matches the payment on amount and date. That is the UTR we just booked.” |
| 8 | 6:20 | GSTR | From `2026-08-01` To `2026-09-30` → **Load summary** → **Download Excel** | “GSTR-1 and 3B worksheets from posted invoices. Preparation only — the CA still files.” |
| 9 | 7:00 | Compliance | **Generate calendar** → mark one row done | “GST and TDS due dates sit next to the deductions we just applied.” |
| 10 | 7:30 | Overview | **Export ledger (Excel)** → open the file for 5 seconds | “This is what goes to the CA: every journal, balanced, with the source documents behind it.” |
| 11 | 8:00 | — | Stop | “Photo in, confirmed books, GST worksheet, ledger out. That is the prototype.” |

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
