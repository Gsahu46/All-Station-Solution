INSERT INTO cities (code, name) VALUES ('pune', 'Pune'), ('mumbai', 'Mumbai'), ('nagpur', 'Nagpur');
INSERT INTO cuisines (id, name) VALUES (1, 'North Indian'), (2, 'South Indian'), (3, 'Chinese'), (4, 'Maharashtrian'), (5, 'Desserts'), (6, 'Street Food');

-- Mumbai: three restaurants written out, so every number on the page can be checked by hand.
INSERT INTO restaurants (city_code, name) VALUES ('mumbai', 'Bombay Canteen'), ('mumbai', 'Anand Stall'), ('mumbai', 'Cafe Madras');
INSERT INTO restaurant_cuisines (restaurant_id, cuisine_id) VALUES (1, 1), (1, 4), (2, 6), (3, 2), (3, 5);
INSERT INTO reviews (restaurant_id, rating) VALUES (1, 5), (1, 4), (1, 4), (3, 3), (3, 5);   -- Anand Stall has no reviews yet

-- Pune: 60 restaurants, each with 2 cuisines and 0 to 4 reviews; the home screen shows 50 of them.
INSERT INTO restaurants (city_code, name) SELECT 'pune', 'Pune Kitchen ' || lpad(i::text, 2, '0') FROM generate_series(1, 60) AS i;
INSERT INTO restaurant_cuisines (restaurant_id, cuisine_id)
    SELECT r.id, c FROM restaurants r, LATERAL (VALUES (r.id % 6 + 1), ((r.id + 2) % 6 + 1)) AS v(c) WHERE r.city_code = 'pune';
INSERT INTO reviews (restaurant_id, rating)
    SELECT r.id, (r.id + k) % 5 + 1 FROM restaurants r, generate_series(1, (r.id % 5)::int) AS k WHERE r.city_code = 'pune';
