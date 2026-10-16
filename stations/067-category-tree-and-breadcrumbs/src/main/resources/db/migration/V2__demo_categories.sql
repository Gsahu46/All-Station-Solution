INSERT INTO categories (id, parent_id, name, slug) VALUES
    (1, NULL, 'Home', 'home'),
    (2, 1, 'Electronics', 'electronics'),
    (3, 2, 'Phones', 'phones'),
    (4, 3, 'Android', 'android'),
    (5, 3, 'iPhone', 'iphone'),
    (6, 2, 'Laptops', 'laptops'),
    (7, 6, 'Gaming Laptops', 'gaming-laptops'),
    (8, 1, 'Fashion', 'fashion'),
    (9, 8, 'Men', 'men'),
    (10, 9, 'Shoes', 'shoes'),
    (11, 8, 'Women', 'women'),
    (12, 11, 'Sarees', 'sarees'),
    (13, 11, 'Shoes', 'shoes');   -- the same slug as 10, under another parent

-- A deep corner: Home > Hobbies > Level 1 > ... > Level 12 (ids 100 to 112).
INSERT INTO categories (id, parent_id, name, slug) VALUES (100, 1, 'Hobbies', 'hobbies');
INSERT INTO categories (id, parent_id, name, slug) SELECT 100 + g, 99 + g, 'Level ' || g, 'level-' || g FROM generate_series(1, 12) AS g;
