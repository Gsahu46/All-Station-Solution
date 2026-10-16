-- Demo customers (invented). Asha already has 120 points.
INSERT INTO customers (id, name) VALUES (1, 'Asha Verma'), (2, 'Rohan Iyer');
INSERT INTO point_entries (customer_id, order_ref, delta, reason) VALUES (1, 'BK-1001', 120, 'EARN');
INSERT INTO point_balances (customer_id, points) VALUES (1, 120);
