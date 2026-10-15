-- Demo sales (products and prices are illustrative). Sale 1 is open for years so the demo always works.
INSERT INTO flash_sales (id, product, stock_total, stock_left, price_paise, starts_at, ends_at) VALUES
    (1, 'Kartwala One 5G, 128 GB', 500, 500, 999900, TIMESTAMPTZ '2026-01-01 00:00 Asia/Kolkata', TIMESTAMPTZ '2030-01-01 00:00 Asia/Kolkata'),
    (2, 'Earbuds Lite', 1000, 0, 49900, TIMESTAMPTZ '2026-01-01 00:00 Asia/Kolkata', TIMESTAMPTZ '2030-01-01 00:00 Asia/Kolkata'),
    (3, 'Smartwatch S', 200, 200, 199900, TIMESTAMPTZ '2026-01-01 12:00 Asia/Kolkata', TIMESTAMPTZ '2026-01-01 12:30 Asia/Kolkata'),
    (4, 'Tablet T10', 100, 100, 1499900, TIMESTAMPTZ '2030-01-01 12:00 Asia/Kolkata', TIMESTAMPTZ '2030-01-01 13:00 Asia/Kolkata');
