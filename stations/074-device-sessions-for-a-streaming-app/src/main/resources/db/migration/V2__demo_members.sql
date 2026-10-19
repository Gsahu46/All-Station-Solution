-- bcrypt hashes made by PostgreSQL's pgcrypto, the same format Spring's BCryptPasswordEncoder reads.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
INSERT INTO members (email, password_hash) VALUES
    ('anika@example.com', '{bcrypt}' || crypt('anika-demo-pass', gen_salt('bf', 10))),
    ('rohan@example.com', '{bcrypt}' || crypt('rohan-demo-pass', gen_salt('bf', 10)));
