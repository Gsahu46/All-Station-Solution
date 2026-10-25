-- Every row belongs to one tenant (one Taskloom customer company). Shared tables, a tenant_id column, and the
-- database itself filtering by it (row-level security) under whatever the application forgets.
CREATE TABLE tenants (
    id   TEXT PRIMARY KEY CONSTRAINT tenants_id_format CHECK (id ~ '^[a-z][a-z0-9-]{1,30}$'),
    name TEXT NOT NULL
);

CREATE TABLE leads (
    id         BIGSERIAL PRIMARY KEY,
    tenant_id  TEXT NOT NULL REFERENCES tenants (id),
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(254) NOT NULL,
    company    VARCHAR(100),
    status     TEXT NOT NULL DEFAULT 'NEW' CONSTRAINT leads_status CHECK (status IN ('NEW', 'CONTACTED', 'QUALIFIED', 'LOST')),
    owner      TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- The same person may be a lead of two companies; within one company, once.
    CONSTRAINT leads_email_unique_per_tenant UNIQUE (tenant_id, email)
);
CREATE INDEX leads_by_tenant ON leads (tenant_id, created_at DESC);

-- The role the application works as. Not the owner and not a superuser, so the policy below applies to it.
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'crm_app') THEN
        CREATE ROLE crm_app LOGIN PASSWORD 'crm_app';
    END IF;
END $$;
GRANT SELECT ON tenants TO crm_app;
GRANT SELECT, INSERT, UPDATE ON leads TO crm_app;
GRANT USAGE ON SEQUENCE leads_id_seq TO crm_app;

-- Rows of the tenant named in this transaction's app.tenant setting, and no others: for reads, and for writes.
-- No setting means no rows (current_setting(..., true) is NULL).
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads FORCE ROW LEVEL SECURITY;
CREATE POLICY leads_tenant_isolation ON leads
    USING (tenant_id = current_setting('app.tenant', true))
    WITH CHECK (tenant_id = current_setting('app.tenant', true));
