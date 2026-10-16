-- Demo sellers, products and one past order (invented).
INSERT INTO sellers (id, name) VALUES (1, 'Chaiwala Traders'), (2, 'Desi Spices Co');
INSERT INTO products (id, seller_id, name, price_paise, created_at, updated_at) VALUES
    (1, 1, 'Assam tea, 500 g',       34900, TIMESTAMPTZ '2026-09-01 10:00 Asia/Kolkata', TIMESTAMPTZ '2026-09-01 10:00 Asia/Kolkata'),
    (2, 1, 'Masala chai mix, 200 g', 19900, TIMESTAMPTZ '2026-09-01 10:00 Asia/Kolkata', TIMESTAMPTZ '2026-09-01 10:00 Asia/Kolkata'),
    (3, 2, 'Kashmiri chilli, 100 g', 12900, TIMESTAMPTZ '2026-09-01 10:00 Asia/Kolkata', TIMESTAMPTZ '2026-09-01 10:00 Asia/Kolkata');
SELECT setval(pg_get_serial_sequence('products', 'id'), 3);
INSERT INTO order_lines (order_ref, product_id, quantity, unit_price_paise) VALUES
    ('KW-1001', 1, 2, 34900),
    ('KW-1001', 2, 1, 19900);
