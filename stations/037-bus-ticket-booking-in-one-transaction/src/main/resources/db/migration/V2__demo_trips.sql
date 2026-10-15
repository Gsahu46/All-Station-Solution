-- Demo trips (routes, times and fares are illustrative).
INSERT INTO trips (id, route, departs_at, seats, fare_paise) VALUES
    (101, 'Pune to Goa', TIMESTAMPTZ '2026-10-20 21:00 Asia/Kolkata', 40, 125000),
    (102, 'Bengaluru to Chennai', TIMESTAMPTZ '2026-10-21 22:30 Asia/Kolkata', 36, 85000);
