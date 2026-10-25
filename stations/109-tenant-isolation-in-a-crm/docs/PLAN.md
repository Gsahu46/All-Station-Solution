# Station 109 plan: Tenant isolation in a CRM

**Problem.** Taskloom's CRM (fictional): a missing WHERE clause in one lookup showed one company's leads to another,
and one endpoint took the tenant from the request body.

**Endpoints.** `GET /leads?status=&q=` (sales or viewer): the caller's company's leads, at most 50, q matched as plain
text (LIKE wildcards escaped). `GET /leads/{id}`: 404 for another company's lead. `POST /leads {name, email, company,
status}` (sales): 201; 409 the email already a lead of this company (emails lower-cased with Locale.ROOT); the same
email at another company is fine. 400 bad input; 401; 403 viewer writing.

**Fix.** The tenant comes from the sign-in only. Every query has WHERE tenant_id = :tenant, and runs in TenantScope:
SET LOCAL ROLE crm_app and set_config('app.tenant', ..., true) in the same transaction, under a FORCE'd row-level
security policy (USING and WITH CHECK). crm_app has no DELETE. Shared tables, tenant column, policy underneath.

**Database.** leads_email_unique_per_tenant, leads_status, tenants_id_format, policy leads_tenant_isolation.

**Trap.** `TenantLeakTrapTest`: the old repository (tenant from the body; a lookup by email with no tenant, as the owner)
plants a lead in Brightpath and returns both companies' rows; the API ignores the body's and query's tenant, and the same
forgetful query inside a tenant's transaction returns only that tenant's row.

**Review.** The scope's SET LOCAL ROLE dropped ("we filter in every query anyway") and the tenant taken from a header.

**Practice.** 1: PATCH a lead's status. 2: notes with a (lead_id, tenant_id) foreign key and their own policy.
3 (paper): when a customer wants its own database.
