-- Demo members (made up): Imran, who will delete his account, and Zoya; and a support agent. Passwords "name-demo-pass".
INSERT INTO users (login, password_hash, role, name, phone, email) VALUES
    ('imran', '{bcrypt}$2a$10$BNBnKBjnnmkSV2yuTGTxh.BSk4Q2hvK8R1HyP4kllGiji63hL7Ay.', 'MEMBER', 'Imran Qureshi', '+919811122233', 'imran.q@example.com'),
    ('zoya', '{bcrypt}$2a$10$ZZXW6UBoaRTR9rA1tZmGGOT6u3.Vn7lEOhILi4LPmCpXdh6MfYL4e', 'MEMBER', 'Zoya Sen', '+919822233344', 'zoya.sen@example.com'),
    ('support', '{bcrypt}$2a$10$qYkPhexCVVT4.rZMRg1sp.1n9tnJ8AyHgW49SsadF39nBzMEY2g7.', 'SUPPORT', 'Support Desk', NULL, NULL);
INSERT INTO profiles VALUES (1, 'Weekend cricket and old Hindi songs', 'Lucknow', '1990-02-14'), (2, 'Book club organiser', 'Pune', '1993-08-30');
INSERT INTO posts (user_id, body) VALUES (1, 'Anyone up for cricket at Gomti Nagar on Sunday? Call me on +919811122233.'), (2, 'Book club meets Friday at 7.');
INSERT INTO comments (post_id, user_id, body) VALUES (1, 2, 'Count me in!'), (2, 1, 'I will bring snacks.');
INSERT INTO invoices (user_id, buyer_name, buyer_phone, amount_paise, issued_on, retain_until) VALUES
    (1, 'Imran Qureshi', '+919811122233', 49900, '2026-04-01', '2033-03-31');
INSERT INTO login_events (user_id, ip, at) VALUES (1, '203.0.113.10', now() - interval '200 days'), (1, '203.0.113.11', now() - interval '2 days');
INSERT INTO otp_requests (phone, code_hash) VALUES ('+919811122233', 'sha256:9f2c...'), ('+919822233344', 'sha256:41ab...');
INSERT INTO contact_uploads (uploader_id, contact_name, contact_phone) VALUES (1, 'Zoya', '+919822233344'), (2, 'Imran cricket', '+919811122233');
INSERT INTO support_tickets (user_id, phone, message) VALUES (1, '+919811122233', 'I cannot change my profile photo.');
INSERT INTO notification_outbox (phone, text) VALUES ('+919811122233', 'Zoya commented on your post');
