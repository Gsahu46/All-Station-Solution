INSERT INTO sellers (id, name) VALUES (7, 'Sharma Electronics'), (8, 'Meera Footwear');
INSERT INTO categories (code, name) VALUES ('phones', 'Phones'), ('shoes', 'Shoes');
INSERT INTO attribute_definitions (category_code, name, required, allowed) VALUES
    ('phones', 'ram', true, ARRAY['4GB', '6GB', '8GB', '12GB']),
    ('phones', 'storage', true, ARRAY['64GB', '128GB', '256GB', '512GB']),
    ('phones', 'colour', false, NULL),
    ('shoes', 'size', true, ARRAY['6', '7', '8', '9', '10', '11']),
    ('shoes', 'colour', true, NULL),
    ('shoes', 'material', false, ARRAY['leather', 'canvas', 'mesh']);

INSERT INTO products (sku, name, category_code, seller_id, price_paise, attributes) VALUES
    ('PH-NOVA-8-128', 'Nova 5G', 'phones', 7, 1899900, '{"ram": "8GB", "storage": "128GB", "colour": "Blue"}'),
    ('PH-NOVA-8-256', 'Nova 5G', 'phones', 7, 2199900, '{"ram": "8GB", "storage": "256GB", "colour": "Blue"}'),
    ('PH-ZEN-6-128', 'Zen Lite', 'phones', 7, 1299900, '{"ram": "6GB", "storage": "128GB"}'),
    ('SH-RUN-9-BLK', 'Road Runner', 'shoes', 8, 349900, '{"size": "9", "colour": "Black", "material": "mesh"}'),
    ('SH-OXF-9-BRN', 'Oxford Classic', 'shoes', 8, 599900, '{"size": "9", "colour": "Brown", "material": "leather"}'),
    ('SH-OXF-10-BRN', 'Oxford Classic', 'shoes', 8, 599900, '{"size": "10", "colour": "Brown", "material": "leather"}');

-- 60,000 generated products, so the plans below are the plans of a real catalog: none with 12GB of RAM, none of size 11.
INSERT INTO products (sku, name, category_code, seller_id, price_paise, attributes)
SELECT 'GEN-' || g, 'Generated ' || g, CASE WHEN g % 2 = 0 THEN 'phones' ELSE 'shoes' END, 7 + g % 2, 100000 + g,
       CASE WHEN g % 2 = 0
            THEN jsonb_build_object('ram', (ARRAY['4GB', '6GB', '8GB'])[g % 3 + 1], 'storage', (ARRAY['64GB', '128GB', '256GB'])[g % 3 + 1])
            ELSE jsonb_build_object('size', (ARRAY['6', '7', '8', '9', '10'])[g % 5 + 1], 'colour', 'Grey') END
FROM generate_series(1, 60000) AS g;
ANALYZE products;
