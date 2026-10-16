INSERT INTO products (id, name) VALUES (1, 'Diya Lamp Set'), (2, 'Rangoli Colours'), (3, 'Dry Fruit Box');

-- Times as Indian Standard Time (+05:30), the shop's zone.
INSERT INTO prices (product_id, price_paise, valid_from, valid_to) VALUES
    (1, 49900, '2026-01-01 00:00+05:30', NULL),
    (2, 19900, '2026-01-01 00:00+05:30', '2026-11-08 00:00+05:30'),
    (2, 14900, '2026-11-08 00:00+05:30', '2026-11-11 00:00+05:30'),   -- the Diwali sale: from midnight on 8 November
    (2, 19900, '2026-11-11 00:00+05:30', NULL),
    (3, 89900, '2026-01-01 00:00+05:30', '2026-06-01 00:00+05:30'),
    (3, 99900, '2026-06-01 00:00+05:30', NULL);
