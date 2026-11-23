# Electrosoft lending pool: handoff notes

## Single source of truth
Google Sheet **Electrosoft Loans Register** (ID `1cB7MrZNVaf-eirOCq13H1nNcbYOLg8Jly1Fnf_rBY20`).
The members' page (`index.html`) is generated from it. Fix the Sheet, never the page.

| Tab | Inputs | Notes |
|---|---|---|
| Loans | A..H, K | One row per loan. Loan ID (e.g. KAG-5), sheet no., member, loan no., date issued (dd/mm/yyyy), advanced, months, interest (as agreed for that loan), first instalment month (`yyyy-mm`, text). I..J and L..N are formulas. |
| Payments | A..F | One row per loan per month with a payment and/or a penalty. Month is `yyyy-mm` text. |
| Shareholders | A..B | Name and shares. C is a formula. |

## Rules
- Instalment = round(total repayable / months). Payments are due by the last day of the month; a month counts as overdue only once it has ended.
- Penalty = one month's interest, charged when nothing is paid in a month. Partial payments are not penalised. Penalties are entered in the Sheet, not calculated by the page.
- No rebate for paying early.
- Interest earned is counted when cash comes in: a payment first clears penalties owed (penalty = income); the rest is split principal/interest in that loan's ratio (interest / total repayable).
- Shareholders' earnings = year's interest + penalties earned, split by shares.

## Rebuild
GitHub Action "Rebuild page from the Sheet" (repo `Achuma640/eletrosoft`, GitHub Pages): three times a day, on any change to tools/ or the workflow, and on demand (Actions tab, Run workflow).
fetch (`tools/fetch_sheet.py`, secret GOOGLE_SA_KEY = service account electrosoft-reader@zaria-village.iam.gserviceaccount.com, its own account, separate from Zaria's; the Sheet is shared with it as Viewer) -> `tools/build.py` (secret ES_PIN) encrypts the data into `index.html` (PBKDF2-SHA256 600k + AES-GCM) and commits only if the Sheet changed.
Local: `python3 tools/build.py DIR --check` validates an export without a PIN.
The PIN is never stored in this repo.
