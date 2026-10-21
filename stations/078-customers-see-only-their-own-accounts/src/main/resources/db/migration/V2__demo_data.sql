-- Demo customers (bcrypt by pgcrypto, the format Spring reads), accounts and September 2026 statement lines.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
INSERT INTO customers (email, name, password_hash) OVERRIDING SYSTEM VALUE VALUES
    ('zoya@example.com', 'Zoya Khan', '{bcrypt}' || crypt('zoya-demo-pass', gen_salt('bf', 10))),
    ('dev@example.com', 'Dev Patel', '{bcrypt}' || crypt('dev-demo-pass', gen_salt('bf', 10))),
    ('ravi@example.com', 'Ravi Kumar', '{bcrypt}' || crypt('ravi-demo-pass', gen_salt('bf', 10)));

INSERT INTO accounts (id, kind, name, balance_paise) VALUES
    (1001, 'savings', 'Zoya Khan', 9850000),
    (1002, 'savings', 'Dev Patel', 1890050),
    (1003, 'savings', 'Zoya Khan and Dev Patel', 7500000),
    (1004, 'current', 'Patel Kirana Stores', 32012575);

INSERT INTO account_holders (account_id, customer_id, access)
SELECT a, c.id, x FROM (VALUES (1001, 'zoya@example.com', 'full'), (1002, 'dev@example.com', 'full'),
                               (1003, 'zoya@example.com', 'full'), (1003, 'dev@example.com', 'full'),
                               (1004, 'dev@example.com', 'full'), (1004, 'ravi@example.com', 'balance_only')) AS h(a, e, x)
JOIN customers c ON c.email = h.e;

INSERT INTO transactions (account_id, booked_on, description, amount_paise) VALUES
    (1001, '2026-09-01', 'Salary, Acme Analytics', 9500000),
    (1001, '2026-09-05', 'Rent, September', -3200000),
    (1001, '2026-09-18', 'UPI to Dev Patel', -150000),
    (1001, '2026-10-02', 'Electricity bill', -245000),
    (1002, '2026-09-03', 'UPI from Zoya Khan', 150000),
    (1002, '2026-09-22', 'Mobile recharge', -59900),
    (1003, '2026-09-10', 'Transfer in, joint savings', 2500000),
    (1004, '2026-09-30', 'Card sales, September', 18250075);
