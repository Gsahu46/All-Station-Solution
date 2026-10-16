INSERT INTO amenities (code, name) VALUES
    ('wifi', 'Free Wi-Fi'), ('pool', 'Swimming pool'), ('breakfast', 'Breakfast included'), ('parking', 'Parking'), ('spa', 'Spa');

-- Prices per night in paise: 3,50,000 paise is Rs 3,500.
INSERT INTO hotels (name, city, stars, price_per_night_paise) VALUES
    ('Calangute Sands', 'goa', 3, 350000),      -- 1
    ('Baga Beach Inn', 'goa', 2, 180000),       -- 2
    ('Panjim Heritage', 'goa', 4, 620000),      -- 3
    ('Candolim Palms', 'goa', 4, 480000),       -- 4
    ('Fort Aguada Resort', 'goa', 5, 1450000),  -- 5
    ('Anjuna Hostel', 'goa', 1, 90000),         -- 6
    ('Pink City Haveli', 'jaipur', 4, 550000),  -- 7
    ('Amber View', 'jaipur', 3, 320000),        -- 8
    ('Rambagh Court', 'jaipur', 5, 2100000);    -- 9

INSERT INTO hotel_amenities (hotel_id, amenity_code) VALUES
    (1, 'wifi'), (1, 'pool'), (1, 'breakfast'),
    (2, 'wifi'),
    (3, 'wifi'), (3, 'breakfast'), (3, 'parking'),
    (4, 'wifi'), (4, 'pool'),
    (5, 'wifi'), (5, 'pool'), (5, 'breakfast'), (5, 'parking'), (5, 'spa'),
    (7, 'wifi'), (7, 'breakfast'),
    (8, 'parking'),
    (9, 'wifi'), (9, 'pool'), (9, 'spa');
