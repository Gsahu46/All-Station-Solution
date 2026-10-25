-- Challenge 2: notes on leads. A note's tenant must be its lead's tenant: a foreign key on both columns.
ALTER TABLE leads ADD CONSTRAINT leads_id_tenant_unique UNIQUE (id, tenant_id);

CREATE TABLE lead_notes (
    id         BIGSERIAL PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    lead_id    BIGINT NOT NULL,
    author     TEXT NOT NULL,
    text       VARCHAR(1000) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT lead_notes_lead_of_same_tenant FOREIGN KEY (lead_id, tenant_id) REFERENCES leads (id, tenant_id)
);
GRANT SELECT, INSERT ON lead_notes TO crm_app;
GRANT USAGE ON SEQUENCE lead_notes_id_seq TO crm_app;
ALTER TABLE lead_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_notes FORCE ROW LEVEL SECURITY;
CREATE POLICY lead_notes_tenant_isolation ON lead_notes
    USING (tenant_id = current_setting('app.tenant', true))
    WITH CHECK (tenant_id = current_setting('app.tenant', true));
