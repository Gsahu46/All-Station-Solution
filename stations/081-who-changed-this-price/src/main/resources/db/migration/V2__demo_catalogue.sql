-- Demo catalogue, imported once. The import is the first revision, so every history starts with the original price.
INSERT INTO products (id, seller, name, price_paise) VALUES
    (1, 'neha.store', 'Aurora 55-inch 4K TV', 5499900),
    (2, 'neha.store', 'Aurora soundbar', 1299900),
    (3, 'arun.mart', 'Steel pressure cooker 5 L', 249900);
INSERT INTO revisions (id, changed_at_ms, changed_by) OVERRIDING SYSTEM VALUE VALUES (1, 1790812800000, 'catalogue.import');
INSERT INTO products_aud (id, rev, revtype, seller, name, price_paise)
SELECT id, 1, 0, seller, name, price_paise FROM products;
ALTER TABLE revisions ALTER COLUMN id RESTART WITH 2;
