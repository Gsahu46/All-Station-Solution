-- Three shipments for one customer, written out so the examples can be checked by hand.
INSERT INTO shipments (awb, phone, booked_on, status) VALUES
    ('DR1000000001', '9876543210', DATE '2026-03-02', 'DELIVERED'),
    ('DR1000000002', '9876543210', DATE '2026-03-15', 'RETURNED'),
    ('DR1000000003', '9876543210', DATE '2026-05-20', 'IN_TRANSIT');

-- 300,000 generated shipments from January to September 2026 (Dakroute has 30 million; the shape is what matters):
-- 270,000 from 90,000 ordinary customers (3 each), and 30,000 from one busy seller, 9123456789.
INSERT INTO shipments (awb, phone, booked_on, status)
SELECT 'DR' || lpad((2000000000 + g)::text, 10, '0'),
       CASE WHEN g <= 30000 THEN '9123456789' ELSE '9' || lpad((g % 90000)::text, 9, '0') END,
       DATE '2026-01-01' + (g * 11 % 273),   -- 11 shares no factor with 273, so every day gets shipments
       (ARRAY['BOOKED', 'IN_TRANSIT', 'DELIVERED', 'DELIVERED', 'DELIVERED', 'RETURNED'])[g % 6 + 1]
FROM generate_series(1, 300000) AS g;
