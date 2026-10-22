-- Demo show: rows E to G, seats 10 to 14. Row F costs more.
INSERT INTO shows (id, title, starts_at) VALUES (1, 'Kalki 2 (Hindi), 7:30 pm', '2026-10-30 14:00:00+00');
INSERT INTO seats (show_id, seat_no, price_paise)
SELECT 1, r || n, CASE r WHEN 'F' THEN 35000 ELSE 25000 END FROM unnest(ARRAY['E', 'F', 'G']) r, generate_series(10, 14) n;
