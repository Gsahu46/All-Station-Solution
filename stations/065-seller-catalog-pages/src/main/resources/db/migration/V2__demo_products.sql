INSERT INTO sellers (id, name) VALUES (7, 'Sharma Electronics'), (8, 'Meera Handlooms');

-- Seller 7: 2,000 products at only 10 different prices and 50 different dates, like real catalogs full of Rs 499.
INSERT INTO products (seller_id, name, price_paise, created_on)
SELECT 7, 'Product ' || lpad(g::text, 4, '0'), 10000 + (g * 7 % 10) * 1000, DATE '2026-01-01' + (g % 50)
FROM generate_series(1, 2000) AS g;

INSERT INTO products (seller_id, name, price_paise, created_on)
SELECT 8, 'Saree ' || lpad(g::text, 2, '0'), 250000 + g * 1000, DATE '2026-02-01' + g FROM generate_series(1, 30) AS g;
