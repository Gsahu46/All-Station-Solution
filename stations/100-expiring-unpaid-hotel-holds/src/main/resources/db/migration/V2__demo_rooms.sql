-- Demo hotel, Ghoomo Goa: 5 deluxe rooms (type 1) and 1 suite (type 2) for each night from 24 to 31 December 2026.
INSERT INTO room_nights (room_type_id, stay_date, total)
SELECT t.id, d::date, t.total
FROM (VALUES (1, 5), (2, 1)) AS t (id, total), generate_series(DATE '2026-12-24', DATE '2026-12-31', INTERVAL '1 day') AS d;
