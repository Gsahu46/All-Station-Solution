# Station 110 plan: Account deletion and data export

**Problem.** Chaupal (fictional community app): a member asked for their data and for deletion under India's DPDP Act;
weeks later their phone number still sat in nine tables: sign-in codes, other members' address-book uploads, unsent
notifications, support tickets. The deletion code had only followed the user id.

**Endpoints.** `POST /me/data-export` (member): 202, a job; `GET /me/data-exports/{id}`: status; `.../file`: the JSON
(409 not ready; 404 someone else's or unknown; 400 a bad id). `DELETE /me`: 202; the account cannot sign in from then
on; the erasure is booked due within 90 days (demo rule) and done by the next job run. 401; 403 for support accounts.

**Fix.** A personal data inventory in code (PersonalData): every table, what links it to a person (user id, phone,
both), and DELETE / ANONYMISE / KEEP_FOR_LAW / NONE with the reason; PersonalDataInventoryTest compares it with
information_schema. The erasure runs it in one transaction; the users row is kept, anonymised (CHECK
users_deleted_holds_nothing). Invoices are kept (tax law), sign-in records 180 days (security). The erasures table is
a ledger with no personal data, to re-apply after a backup restore. Logs carry ids only.

**Trap.** `AccountDeletionTrapTest`: the old delete-by-user-id leaves the number in contact_uploads,
notification_outbox and otp_requests (and invoices, by law); the API leaves it only in invoices. Found by scanning
every text column of every table.

**Review.** The inventory driven by foreign keys to users ("everything personal points at users").

**Practice.** 1: exports expire after 7 days (410). 2: inactive accounts: a notice, then erasure after 48 hours.
3 (paper): a backup restored after erasures.
