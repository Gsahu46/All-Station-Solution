-- Two demo customer companies and their leads (made up). The policy applies to these inserts too: each tenant's rows
-- are written with that tenant set.
INSERT INTO tenants (id, name) VALUES ('zestful', 'Zestful Foods'), ('brightpath', 'Brightpath Tutors');

SELECT set_config('app.tenant', 'zestful', true);
INSERT INTO leads (tenant_id, name, email, company, status, owner) VALUES
    ('zestful', 'Rahul Mehta', 'rahul@spicehub.example', 'Spice Hub', 'QUALIFIED', 'ananya'),
    ('zestful', 'Leela Thomas', 'leela@greenbowl.example', 'Green Bowl Cafe', 'NEW', 'ananya');

SELECT set_config('app.tenant', 'brightpath', true);
INSERT INTO leads (tenant_id, name, email, company, status, owner) VALUES
    ('brightpath', 'Sunil Rao', 'sunil.rao@example.org', 'Sunrise School', 'CONTACTED', 'farhan'),
    ('brightpath', 'Rahul Mehta', 'rahul@spicehub.example', 'Spice Hub', 'NEW', 'farhan');
