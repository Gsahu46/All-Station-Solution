-- bcrypt hashes made by PostgreSQL's pgcrypto, the same format Spring's BCryptPasswordEncoder reads.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
INSERT INTO candidates (email, full_name, password_hash, status) VALUES
    ('priya@example.com', 'Priya Nair', '{bcrypt}' || crypt('priya-old-password', gen_salt('bf', 10)), 'ACTIVE'),
    ('arjun@example.com', 'Arjun Mehta', '{bcrypt}' || crypt('arjun-old-password', gen_salt('bf', 10)), 'ACTIVE'),
    ('kiran@example.com', 'Kiran Das', '{bcrypt}' || crypt('kiran-old-password', gen_salt('bf', 10)), 'SUSPENDED');
