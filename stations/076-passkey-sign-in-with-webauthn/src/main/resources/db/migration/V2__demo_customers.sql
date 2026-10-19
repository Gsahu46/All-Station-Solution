-- Demo customers. bcrypt by pgcrypto (the format Spring reads). The TOTP secret is RFC 6238's published test secret,
-- "12345678901234567890" (base32 GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ): demo only, so anyone can compute the codes.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
INSERT INTO customers (email, name, user_handle, password_hash, totp_secret, balance_paise) VALUES
    ('zoya@example.com', 'Zoya Khan', gen_random_bytes(32), '{bcrypt}' || crypt('zoya-demo-pass', gen_salt('bf', 10)), convert_to('12345678901234567890', 'UTF8'), 4250000),
    ('dev@example.com', 'Dev Patel', gen_random_bytes(32), '{bcrypt}' || crypt('dev-demo-pass', gen_salt('bf', 10)), convert_to('12345678901234567890', 'UTF8'), 1890050);
