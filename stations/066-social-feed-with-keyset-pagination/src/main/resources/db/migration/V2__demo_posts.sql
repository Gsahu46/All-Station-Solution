INSERT INTO authors (id, handle) VALUES (1, 'asha_writes'), (2, 'kabir'), (3, 'meera_k'), (4, 'ravi_07');

-- 100,000 posts over about 5.5 hours, five per second: posts made in the same second share a timestamp,
-- as they do when an app imports a batch or a server's clock only has second precision.
INSERT INTO posts (author_id, body, created_at)
SELECT g % 4 + 1, 'Post number ' || g, TIMESTAMPTZ '2026-10-01 00:00:00+00' + make_interval(secs => g / 5)
FROM generate_series(1, 100000) AS g;
ANALYZE posts;
