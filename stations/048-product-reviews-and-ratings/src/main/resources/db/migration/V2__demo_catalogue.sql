-- Demo catalogue and customers (invented). Purchases: Asha and Vikram have the headphones delivered; Neha's are on
-- the way; Imran never bought them.
INSERT INTO products (id, name) VALUES
    (1, 'Wireless headphones, 40 h battery'),
    (2, 'Steel water bottle, 1 litre'),
    (3, 'Cotton bedsheet, double');
INSERT INTO product_ratings (product_id) SELECT id FROM products;
INSERT INTO customers (id, name) VALUES
    (1, 'Asha Verma'), (2, 'Vikram Rao'), (3, 'Neha Kulkarni'), (4, 'Imran Shaikh');
INSERT INTO purchases (id, customer_id, product_id, delivered_on) VALUES
    (1, 1, 1, DATE '2026-09-28'),
    (2, 2, 1, DATE '2026-10-02'),
    (3, 3, 1, NULL),
    (4, 1, 3, DATE '2026-10-05');
