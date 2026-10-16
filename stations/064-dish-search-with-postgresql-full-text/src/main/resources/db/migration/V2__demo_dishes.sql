-- Pune: dishes written out, so every search on the page can be checked by hand.
INSERT INTO dishes (city, restaurant, name, description, price_paise) VALUES
    ('pune', 'Punjab Grill', 'Paneer Tikka Masala', 'Grilled cottage cheese in a spiced tomato gravy', 32000),
    ('pune', 'Punjab Grill', 'Paneer Tikka', 'Cottage cheese cubes marinated and grilled in the tandoor', 28000),
    ('pune', 'Punjab Grill', 'Butter Chicken', 'Our best seller after the paneer tikka: chicken in a buttery tomato gravy', 34000),
    ('pune', 'Tandoor Express', 'Tandoori Paneer Tikka Roll', 'Paneer tikka wrapped in a rumali roti', 18000),
    ('pune', 'Vaishali', 'Masala Dosa', 'Crisp rice crepe with spiced potato', 12000),
    ('pune', 'Vaishali', 'Mysore Masala Dosa', 'With a red chutney spread inside', 14000),
    ('pune', 'Vaishali', 'Filter Coffee', NULL, 5000),
    ('mumbai', 'Bandra Bites', 'Paneer Tikka Pizza', 'Thin crust with paneer tikka and onions', 42000);

-- 200,000 generated dishes in three cities (Tiffino has 3 million): none mentions paneer, tikka or dosa.
INSERT INTO dishes (city, restaurant, name, description, price_paise)
SELECT (ARRAY['pune', 'mumbai', 'delhi'])[g % 3 + 1],
       'Kitchen ' || (g % 5000),
       (ARRAY['Veg', 'Chicken', 'Mutton', 'Egg', 'Fish'])[g % 5 + 1] || ' ' || (ARRAY['Biryani', 'Curry', 'Thali', 'Fried Rice', 'Noodles', 'Roll', 'Kebab'])[g % 7 + 1],
       'House special number ' || g,
       10000 + (g % 40) * 1000
FROM generate_series(1, 200000) AS g;
