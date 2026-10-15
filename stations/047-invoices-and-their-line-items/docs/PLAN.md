# Station 047 plan: Invoices and their line items

**Problem.** Billora's "edit lines" cleared the invoice's list and added the corrected lines. The mapping had cascade
ALL but no orphanRemoval, so the old rows stayed in invoice_lines with their invoice_id: the next read brought them
back, and both the invoice total and the finance report (a SUM over the table) counted them.

**Endpoints.** `POST /invoices` {customerName 1-80, lines 1-50 [{description 1-120, quantity 1-10000, unitPricePaise
1..10^10}]} 201 + Location; `PUT /invoices/{id}/lines` {lines} replaces all, 200; `GET /invoices/{id}` 200/404. Totals
computed from lines (quantity × unit price, paise). 400 bad body, including 1500.50 for a paise field
(accept-float-as-int off, found while building: Jackson truncated it by default).

**Code.** Invoice @OneToMany(mappedBy, cascade ALL, orphanRemoval) @OrderBy id, unmodifiable getter, addLine/
replaceLines helpers that set both sides; InvoiceLine @ManyToOne LAZY optional=false; findWithLinesById @EntityGraph.

**Database.** invoices_customer_not_blank; invoice_lines_invoice_fk (no cascade delete), _quantity_range, _price_range.

**Tests.** OrphanLinesTrapTest (test-only OldInvoice mapping on the same tables: 4 rows and ₹24,998 after the old
replace; 2 rows with the fix; adding to the list without the back reference fails on invoice_id), InvoiceContractTest,
InvoiceDatabaseTest (constraints, a refused replacement keeps the old lines, one query to read). Mutations:
orphanRemoval off -> 2 red; no back reference -> 9; no entity graph -> 1; replacing the list object -> 2 (Hibernate: "A
collection with orphan deletion was no longer referenced").

**Practice.** 1: remove one line by position (409 for the last). 2: tax per line, rounded half up, V2 migration.
Design: editing issued invoices (credit notes instead of edits).
