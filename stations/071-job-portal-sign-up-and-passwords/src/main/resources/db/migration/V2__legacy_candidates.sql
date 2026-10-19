-- Two accounts imported from the old system, still carrying its unsalted MD5 hashes (of "summer2024!" and "Hireloop@123").
-- Each is upgraded to bcrypt the first time its owner signs in.
INSERT INTO candidates (email, full_name, password_hash) VALUES
    ('priya@example.com', 'Priya Nair', '{MD5}' || md5('summer2024!')),
    ('arjun@example.com', 'Arjun Mehta', '{MD5}' || md5('Hireloop@123'));
